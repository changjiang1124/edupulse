"""Help Centre article registry.

Articles are ordered as a step-by-step guide. Each article body lives in
templates/help_centre/articles/<slug>.html and screenshots in
static/help_centre/img/.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Article:
    slug: str
    title: str
    audience: str
    summary: str

    @property
    def template_name(self):
        return f"help_centre/articles/{self.slug.replace('-', '_')}.html"


ARTICLES = [
    Article(
        slug='add-a-teacher',
        title='Add a teacher',
        audience='Administrators',
        summary='Create a login for a new teacher so they can clock in and out.',
    ),
    Article(
        slug='set-up-a-campus',
        title='Set up a campus for clock-in',
        audience='Administrators',
        summary='Save the campus location once, so EduPulse can check that teachers are on site.',
    ),
    Article(
        slug='clock-in-and-out',
        title='Clock in and out',
        audience='Teachers',
        summary='Record the start and end of a shift from your phone.',
    ),
    Article(
        slug='check-and-correct-hours',
        title='Check and correct hours',
        audience='Administrators',
        summary='Review everyone\'s hours, fix a wrong time or add a missed shift.',
    ),
    Article(
        slug='export-timesheets',
        title='Export timesheets',
        audience='Administrators and teachers',
        summary='Download hours to Excel for payroll or your own records.',
    ),
]

ARTICLES_BY_SLUG = {article.slug: article for article in ARTICLES}


def get_neighbours(slug):
    """Return (previous, next) articles for step navigation."""
    index = [article.slug for article in ARTICLES].index(slug)
    previous_article = ARTICLES[index - 1] if index > 0 else None
    next_article = ARTICLES[index + 1] if index + 1 < len(ARTICLES) else None
    return previous_article, next_article
