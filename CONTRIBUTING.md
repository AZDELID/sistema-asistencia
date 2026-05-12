# Contributing

Thank you for your interest in contributing to this project.

## Development setup

```bash
git clone git@github.com:Wil-1302/Sistema-de-control-de-asistencia.git
cd Sistema-de-control-de-asistencia
python3.14 -m venv venv
source venv/bin/activate
bash install_314.sh          # Python 3.14 / Arch Linux
# or: pip install -r requirements.txt && pip install --no-deps facenet-pytorch==2.6.0
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Workflow

1. Fork the repository and create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes. Run the system check before committing:
   ```bash
   python manage.py check
   python manage.py test app1
   ```
3. Write a clear commit message describing the *why*, not just the *what*.
4. Push your branch and open a Pull Request against `main`.

## Code style

- Follow PEP 8. Keep lines under 100 characters.
- No unused imports. No commented-out dead code left in PRs.
- Django views: keep business logic out of templates; keep ML logic out of views where possible.
- JS: plain ES6+, no framework required. Keep it in `{% block extra_js %}`.

## Model changes

After modifying `app1/models.py`, always run:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py check
```

Commit the migration file together with the model change.

## Security

- Never commit `.env`, `db.sqlite3`, or `media/` files.
- Never hardcode credentials or secret keys.
- Report security vulnerabilities privately to the maintainer before opening a public issue.

## ML / camera changes

- Test with at least one authorized student before submitting.
- The worker must not crash on a bad frame — wrap new per-frame logic in `try/except` and log errors.
- Verify `len(known_enc) == len(known_names)` is maintained after any change to `_get_known_embeddings`.

## License

By contributing you agree that your contributions will be licensed under the MIT License.
