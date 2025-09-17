// EduPulse 自定义JavaScript功能

$(document).ready(function() {
    // 初始化所有工具提示
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // 初始化所有弹出框
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // 自动关闭警告消息
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);

    // 搜索功能增强
    $('.search-input').on('input', function() {
        var searchTerm = $(this).val().toLowerCase();
        var targetTable = $(this).data('target');
        
        $(targetTable + ' tbody tr').each(function() {
            var rowText = $(this).text().toLowerCase();
            if (rowText.indexOf(searchTerm) > -1) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    });

    // 表格行点击事件
    $('.clickable-row').click(function() {
        window.location = $(this).data('href');
    });

    // 确认删除对话框
    $('.delete-btn').click(function(e) {
        e.preventDefault();
        var itemName = $(this).data('item');
        var deleteUrl = $(this).attr('href');
        
        if (confirm('确定要删除 "' + itemName + '" 吗？此操作无法撤销。')) {
            window.location = deleteUrl;
        }
    });

    // 表单提交加载状态
    $('form').submit(function() {
        var submitBtn = $(this).find('button[type="submit"]');
        submitBtn.prop('disabled', true);
        submitBtn.html('<span class="spinner-border spinner-border-sm me-2" role="status"></span>Processing...');
    });

    // 数据表格排序
    $('.sortable-table th[data-sort]').click(function() {
        var table = $(this).parents('table');
        var rows = table.find('tbody tr').toArray();
        var column = $(this).data('sort');
        var isAsc = $(this).hasClass('asc');
        
        rows.sort(function(a, b) {
            var aVal = $(a).find('td').eq(column).text();
            var bVal = $(b).find('td').eq(column).text();
            
            if (isAsc) {
                return aVal.localeCompare(bVal);
            } else {
                return bVal.localeCompare(aVal);
            }
        });
        
        // 更新排序图标
        $('.sortable-table th').removeClass('asc desc');
        $(this).addClass(isAsc ? 'desc' : 'asc');
        
        // 重新排列行
        $.each(rows, function(index, row) {
            table.children('tbody').append(row);
        });
    });

    // 批量选择功能
    $('.select-all').change(function() {
        var checkboxes = $(this).closest('table').find('.row-select');
        checkboxes.prop('checked', $(this).prop('checked'));
        updateBatchActions();
    });

    $('.row-select').change(function() {
        updateBatchActions();
    });

    function updateBatchActions() {
        var selectedRows = $('.row-select:checked').length;
        var batchActions = $('.batch-actions');
        
        if (selectedRows > 0) {
            batchActions.removeClass('d-none');
            batchActions.find('.selected-count').text(selectedRows);
        } else {
            batchActions.addClass('d-none');
        }
    }

    // AJAX表单处理
    $('.ajax-form').submit(function(e) {
        e.preventDefault();
        var form = $(this);
        var formData = new FormData(this);
        
        $.ajax({
            url: form.attr('action'),
            type: form.attr('method'),
            data: formData,
            processData: false,
            contentType: false,
            beforeSend: function() {
                form.find('.submit-btn').prop('disabled', true);
                form.find('.loading-spinner').removeClass('d-none');
            },
            success: function(response) {
                if (response.success) {
                    showNotification('success', response.message || '操作成功！');
                    if (response.redirect) {
                        setTimeout(function() {
                            window.location = response.redirect;
                        }, 1500);
                    }
                } else {
                    showNotification('error', response.message || '操作失败，请重试。');
                }
            },
            error: function(xhr, status, error) {
                showNotification('error', '网络错误，请检查连接后重试。');
            },
            complete: function() {
                form.find('.submit-btn').prop('disabled', false);
                form.find('.loading-spinner').addClass('d-none');
            }
        });
    });

    // 通知消息函数
    function showNotification(type, message) {
        var alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
        var notification = '<div class="alert ' + alertClass + ' alert-dismissible fade show" role="alert">' +
                          message +
                          '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>' +
                          '</div>';
        
        $('.notification-area').html(notification);
        setTimeout(function() {
            $('.alert').fadeOut();
        }, 5000);
    }

    // 日期选择器本地化
    if ($.fn.datepicker) {
        $('.datepicker').datepicker({
            format: 'yyyy-mm-dd',
            language: 'zh-CN',
            autoclose: true,
            todayHighlight: true
        });
    }

    // 时间选择器
    if ($.fn.timepicker) {
        $('.timepicker').timepicker({
            format: 'HH:mm',
            interval: 15,
            minTime: '08:00',
            maxTime: '22:00',
            defaultTime: '09:00',
            startTime: '08:00',
            dynamic: false,
            dropdown: true,
            scrollbar: true
        });
    }

    // 文件上传预览
    $('.file-input').change(function() {
        var input = this;
        var preview = $(this).siblings('.file-preview');
        
        if (input.files && input.files[0]) {
            var reader = new FileReader();
            
            reader.onload = function(e) {
                var fileType = input.files[0].type;
                if (fileType.match('image.*')) {
                    preview.html('<img src="' + e.target.result + '" class="img-thumbnail" style="max-width: 200px;">');
                } else {
                    preview.html('<p>文件已选择: ' + input.files[0].name + '</p>');
                }
                preview.removeClass('d-none');
            };
            
            reader.readAsDataURL(input.files[0]);
        }
    });

    // 自动保存草稿功能
    var autoSaveTimer;
    $('.auto-save').on('input', function() {
        clearTimeout(autoSaveTimer);
        var form = $(this).closest('form');
        
        autoSaveTimer = setTimeout(function() {
            saveDraft(form);
        }, 3000); // 3秒后自动保存
    });

    function saveDraft(form) {
        var formData = form.serialize();
        var saveUrl = form.data('draft-url');
        
        if (saveUrl) {
            $.ajax({
                url: saveUrl,
                type: 'POST',
                data: formData,
                success: function() {
                    showNotification('info', '草稿已自动保存');
                }
            });
        }
    }

    // 打印功能
    $('.print-btn').click(function() {
        window.print();
    });

    // 导出功能
    $('.export-btn').click(function() {
        var exportUrl = $(this).data('export-url');
        var format = $(this).data('format');
        
        if (exportUrl) {
            window.open(exportUrl + '?format=' + format, '_blank');
        }
    });

    // 仪表盘数据刷新
    $('.refresh-data').click(function() {
        var widget = $(this).closest('.dashboard-widget');
        var refreshUrl = $(this).data('refresh-url');
        
        if (refreshUrl) {
            widget.find('.loading-overlay').removeClass('d-none');
            
            $.ajax({
                url: refreshUrl,
                success: function(data) {
                    widget.find('.widget-content').html(data);
                },
                complete: function() {
                    widget.find('.loading-overlay').addClass('d-none');
                }
            });
        }
    });

    // 移动端菜单优化
    if (window.innerWidth <= 768) {
        $('.navbar-nav .dropdown').on('click', function(e) {
            e.stopPropagation();
            $(this).find('.dropdown-menu').toggleClass('show');
        });
    }

    // 页面加载完成后的动画
    $('.fade-in').each(function(i) {
        var element = $(this);
        setTimeout(function() {
            element.addClass('show');
        }, i * 100);
    });
});

// GPS定位功能（用于打卡系统）
function getCurrentLocation() {
    return new Promise(function(resolve, reject) {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    resolve({
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude
                    });
                },
                function(error) {
                    reject(error);
                }
            );
        } else {
            reject(new Error('Geolocation is not supported by this browser.'));
        }
    });
}

// 二维码扫描功能
function initQRScanner(containerId, callback) {
    // 这里可以集成如QuaggaJS或ZXing等二维码扫描库
    // 为简化，这里只是一个占位符
    console.log('QR Scanner initialized for container:', containerId);
    
    // 示例回调
    if (callback) {
        setTimeout(function() {
            callback('sample-qr-code-data');
        }, 2000);
    }
}

// 实时数据更新（WebSocket连接）
function initWebSocket() {
    // 如果需要实时更新功能，可以在这里建立WebSocket连接
    console.log('WebSocket connection initialized');
}