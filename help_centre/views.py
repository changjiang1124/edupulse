from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.views.generic import TemplateView

from accounts.mixins import TeacherOrAdminRequiredMixin

from .articles import ARTICLES, ARTICLES_BY_SLUG, get_neighbours


class HelpCentreIndexView(LoginRequiredMixin, TeacherOrAdminRequiredMixin, TemplateView):
    template_name = 'help_centre/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['articles'] = ARTICLES
        return context


class HelpArticleView(LoginRequiredMixin, TeacherOrAdminRequiredMixin, TemplateView):
    template_name = 'help_centre/article.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        article = ARTICLES_BY_SLUG.get(kwargs['slug'])
        if article is None:
            raise Http404('Help article not found')
        previous_article, next_article = get_neighbours(article.slug)
        context.update({
            'article': article,
            'articles': ARTICLES,
            'step_number': ARTICLES.index(article) + 1,
            'previous_article': previous_article,
            'next_article': next_article,
        })
        return context
