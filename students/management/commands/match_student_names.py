import csv
import re
import difflib
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from students.models import Student


class Command(BaseCommand):
    help = 'Match names from TSV file with students in database and generate results file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--input',
            type=str,
            default='poster-name-match.tsv',
            help='Path to the input TSV file (default: poster-name-match.tsv)'
        )
        parser.add_argument(
            '--output',
            type=str,
            default='poster-name-match-results.tsv',
            help='Path to the output TSV file (default: poster-name-match-results.tsv)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview matching results without creating output file'
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=0.6,
            help='Minimum confidence threshold for fuzzy matching (0.0-1.0, default: 0.6)'
        )

    def handle(self, *args, **options):
        input_file = options['input']
        output_file = options['output']
        dry_run = options['dry_run']
        threshold = options['threshold']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No output file will be created'))

        try:
            # Load all students once for efficiency
            self.students = list(Student.objects.filter(is_active=True))
            self.student_names = [(s.get_full_name(), s) for s in self.students]

            self.stdout.write(f'加载了 {len(self.students)} 名活跃学生进行匹配')

            with open(input_file, 'r', encoding='utf-8') as file:
                results = self.match_names(file, threshold)

            if not dry_run:
                self.write_results(results, output_file)

            self.print_summary(results, dry_run)

        except FileNotFoundError:
            raise CommandError(f'文件未找到: {input_file}')
        except Exception as e:
            raise CommandError(f'处理文件时出错: {str(e)}')

    def match_names(self, file, threshold):
        """Match names from input file with student database"""
        reader = csv.reader(file, delimiter='\t')

        # Skip header if exists
        first_row = next(reader, None)
        if first_row and first_row[0].lower().strip() in ['name', 'student_name', 'du_poster_name']:
            # Header detected, continue with next row
            pass
        else:
            # No header, reset file pointer and process first row
            file.seek(0)
            reader = csv.reader(file, delimiter='\t')

        results = []

        for row_num, row in enumerate(reader, start=1):
            if not row or not row[0].strip():
                continue

            poster_name = row[0].strip()
            match_result = self.find_best_match(poster_name, threshold)

            results.append({
                'row_num': row_num,
                'poster_name': poster_name,
                'matched_name': match_result['matched_name'],
                'student_id': match_result['student_id'],
                'match_type': match_result['match_type'],
                'confidence_score': match_result['confidence_score']
            })

            # Print progress for dry run
            if match_result['matched_name']:
                self.stdout.write(
                    f"第 {row_num} 行: '{poster_name}' → '{match_result['matched_name']}' "
                    f"({match_result['match_type']}, {match_result['confidence_score']:.0%})"
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"第 {row_num} 行: '{poster_name}' → 未找到匹配")
                )

        return results

    def find_best_match(self, poster_name, threshold):
        """Find the best matching student name using multiple strategies"""

        # Strategy 1: Exact match
        exact_match = self.exact_match(poster_name)
        if exact_match:
            return exact_match

        # Strategy 2: Normalized match (case insensitive, strip spaces/punctuation)
        normalized_match = self.normalized_match(poster_name)
        if normalized_match:
            return normalized_match

        # Strategy 3: Fuzzy match with confidence scoring
        fuzzy_match = self.fuzzy_match(poster_name, threshold)
        if fuzzy_match:
            return fuzzy_match

        # Strategy 4: Partial match (first name or last name)
        partial_match = self.partial_match(poster_name, threshold)
        if partial_match:
            return partial_match

        # No match found
        return {
            'matched_name': '',
            'student_id': '',
            'match_type': 'none',
            'confidence_score': 0.0
        }

    def exact_match(self, poster_name):
        """Find exact name match"""
        for student_name, student in self.student_names:
            if poster_name == student_name:
                return {
                    'matched_name': student_name,
                    'student_id': student.id,
                    'match_type': 'exact',
                    'confidence_score': 1.0
                }
        return None

    def normalized_match(self, poster_name):
        """Find match after normalizing names (case, spaces, punctuation)"""
        normalized_poster = self.normalize_name(poster_name)

        for student_name, student in self.student_names:
            normalized_student = self.normalize_name(student_name)
            if normalized_poster == normalized_student:
                return {
                    'matched_name': student_name,
                    'student_id': student.id,
                    'match_type': 'normalized',
                    'confidence_score': 0.95
                }
        return None

    def fuzzy_match(self, poster_name, threshold):
        """Find fuzzy match using string similarity"""
        best_match = None
        best_score = 0.0

        normalized_poster = self.normalize_name(poster_name)

        for student_name, student in self.student_names:
            normalized_student = self.normalize_name(student_name)

            # Calculate similarity using SequenceMatcher
            similarity = difflib.SequenceMatcher(None, normalized_poster, normalized_student).ratio()

            if similarity > best_score and similarity >= threshold:
                best_score = similarity
                best_match = {
                    'matched_name': student_name,
                    'student_id': student.id,
                    'match_type': 'fuzzy',
                    'confidence_score': similarity
                }

        return best_match

    def partial_match(self, poster_name, threshold):
        """Find partial match (first name or last name)"""
        name_parts = poster_name.strip().split()
        if not name_parts:
            return None

        best_match = None
        best_score = 0.0

        for student_name, student in self.student_names:
            student_parts = student_name.split()

            # Check if any part of poster name matches any part of student name
            for poster_part in name_parts:
                for student_part in student_parts:
                    if len(poster_part) >= 3 and len(student_part) >= 3:  # Only match meaningful parts
                        similarity = difflib.SequenceMatcher(
                            None,
                            self.normalize_name(poster_part),
                            self.normalize_name(student_part)
                        ).ratio()

                        if similarity > best_score and similarity >= threshold:
                            best_score = similarity
                            best_match = {
                                'matched_name': student_name,
                                'student_id': student.id,
                                'match_type': 'partial',
                                'confidence_score': similarity * 0.8  # Reduce confidence for partial matches
                            }

        return best_match

    def normalize_name(self, name):
        """Normalize name for comparison (lowercase, remove spaces and punctuation)"""
        if not name:
            return ''

        # Convert to lowercase and remove extra spaces
        normalized = re.sub(r'\s+', ' ', name.lower().strip())

        # Remove common punctuation
        normalized = re.sub(r'[^\w\s]', '', normalized)

        # Handle common name variations
        name_variations = {
            'katherine': 'kate',
            'katharine': 'kate',
            'catherine': 'kate',
            'william': 'bill',
            'william': 'will',
            'robert': 'bob',
            'richard': 'rick',
            'richard': 'dick',
            'elizabeth': 'liz',
            'elizabeth': 'beth',
            'margaret': 'meg',
            'margaret': 'maggie',
            'christopher': 'chris',
            'michael': 'mike',
            'michelle': 'mich',
            'stephanie': 'steph',
            'rebecca': 'becca',
            'rebecca': 'becky',
            'patricia': 'pat',
            'patricia': 'patty'
        }

        # Apply name variations
        for full_name, short_name in name_variations.items():
            normalized = normalized.replace(full_name, short_name)

        return normalized

    def write_results(self, results, output_file):
        """Write matching results to output TSV file"""
        try:
            with open(output_file, 'w', encoding='utf-8', newline='') as file:
                writer = csv.writer(file, delimiter='\t')

                # Write header
                writer.writerow([
                    'poster_name',
                    'matched_name',
                    'student_id',
                    'match_type',
                    'confidence_score'
                ])

                # Write results
                for result in results:
                    writer.writerow([
                        result['poster_name'],
                        result['matched_name'],
                        result['student_id'],
                        result['match_type'],
                        f"{result['confidence_score']:.2f}"
                    ])

            self.stdout.write(
                self.style.SUCCESS(f'结果已保存到: {output_file}')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'写入结果文件时出错: {str(e)}')
            )

    def print_summary(self, results, dry_run):
        """Print matching summary statistics"""
        total = len(results)
        matched = len([r for r in results if r['matched_name']])
        unmatched = total - matched

        # Count by match type
        match_types = {}
        for result in results:
            match_type = result['match_type']
            match_types[match_type] = match_types.get(match_type, 0) + 1

        # Calculate average confidence for matched results
        matched_results = [r for r in results if r['matched_name']]
        avg_confidence = sum(r['confidence_score'] for r in matched_results) / len(matched_results) if matched_results else 0

        self.stdout.write('\n' + '=' * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING('匹配结果预览'))
        else:
            self.stdout.write(self.style.SUCCESS('匹配完成'))

        self.stdout.write(f"总计处理姓名: {total}")
        self.stdout.write(self.style.SUCCESS(f"找到匹配: {matched} ({matched/total*100:.1f}%)"))
        self.stdout.write(self.style.WARNING(f"未找到匹配: {unmatched} ({unmatched/total*100:.1f}%)"))

        if matched_results:
            self.stdout.write(f"平均置信度: {avg_confidence:.1%}")

        self.stdout.write('\n匹配类型统计:')
        for match_type, count in sorted(match_types.items()):
            if match_type != 'none':
                self.stdout.write(f"  {match_type}: {count}")

        if dry_run and matched > 0:
            self.stdout.write('\n' + self.style.WARNING('要生成结果文件，请运行命令时不带 --dry-run 参数'))