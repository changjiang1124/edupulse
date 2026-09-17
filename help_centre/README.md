# Help Centre

In-app user guides at `/help/`, visible to logged-in teachers and administrators.

## Edit a guide

Guide bodies are plain Django templates in `templates/help_centre/articles/`. Edit the HTML and deploy.
The page title, audience and summary come from `help_centre/articles.py`.

Conventions used in the existing guides:

- One `<ol class="help-steps">` per task. Each `<li>` is one action.
- Wrap on-screen labels (buttons, menu items, field names) in `<span class="help-ui">`. Use the exact wording from the screen.
- Screenshots go inside the step they illustrate:
  ```html
  <figure class="help-figure">
      <img class="help-screenshot" src="{% static 'help_centre/img/<name>.png' %}" alt="What the screenshot shows" loading="lazy">
  </figure>
  ```
  Add `help-screenshot--phone` for phone screenshots. Put two phone screenshots side by side in `<div class="help-figure-row">`.
- Use Bootstrap alerts for warnings (`alert-warning`) and tips (`alert-info`).
- Link to another guide with `{% url 'help_centre:article' '<slug>' %}`.
- Australian English, short sentences, no icons.

## Add a guide

1. Add an `Article(...)` to `ARTICLES` in `help_centre/articles.py`. The list order is the order shown on the index page and the Previous/Next links.
2. Create `templates/help_centre/articles/<slug with underscores>.html`, starting with `{% load static %}`.
3. Add screenshots to `static/help_centre/img/`. Keep them small: phone shots about 720 px wide, desktop shots about 1600 px wide, compressed with pngquant.
4. Run `python manage.py test help_centre`. It checks that every guide renders and that every screenshot it references exists.

## Screenshots

The current screenshots are generated from fake data. See `screenshots/README.md` to regenerate them after a screen changes.
You can also replace a single image by hand, as long as it keeps the same file name.
