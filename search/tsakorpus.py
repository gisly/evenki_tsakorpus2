# WSGI entrypoint used by gunicorn inside the docker container.
#
# The upstream tsakorpus.wsgi alongside this file has hardcoded /home/gisly/...
# paths and the .wsgi extension makes it non-importable by gunicorn.
# This file is path-agnostic AND mounts the Flask app at a URL prefix
# (default /corpus) so it lives at https://gisly.net/corpus.
#
# How the prefix works:
#   - The Flask app's @app.route('/foo') decorators stay unchanged.
#   - werkzeug's DispatcherMiddleware wraps the app so that '/corpus/foo'
#     dispatches to the Flask app's '/foo'.
#   - url_for() and Flask's static URL builder automatically prepend
#     '/corpus' once APPLICATION_ROOT is set.
#   - Templates that use relative URLs (the tsakorpus convention) Just Work
#     because the browser resolves them against the current page path.
#
# To change or disable the prefix, set TSAKORPUS_PREFIX in the environment.
# An empty string or '/' mounts the app at the root.

import sys
import os

APP_PREFIX = os.environ.get("TSAKORPUS_PREFIX", "/corpus")

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from web_app import app as flask_app, get_locale as app_get_locale
from flask_babel import Babel

babel = Babel(flask_app)
babelOldVersion = ('localeselector' in Babel.__dict__)

if babelOldVersion:
    @babel.localeselector
    def get_locale():
        return app_get_locale()
    babel.init_app(flask_app)
else:
    def get_locale():
        return app_get_locale()
    babel.init_app(flask_app, locale_selector=get_locale)


flask_app.config["APPLICATION_ROOT"] = APP_PREFIX or "/"


if APP_PREFIX and APP_PREFIX != "/":
    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    from werkzeug.wrappers import Response

    def _root_404(environ, start_response):
        resp = Response(
            "Not found. The corpus lives at {}/".format(APP_PREFIX),
            status=404,
            mimetype="text/plain",
        )
        return resp(environ, start_response)

    application = DispatcherMiddleware(_root_404, {APP_PREFIX: flask_app})
else:
    application = flask_app


if __name__ == "__main__":
    # Useful for `docker compose exec tsakorpus python search/tsakorpus.py`
    flask_app.run(port=7342, host='0.0.0.0', debug=False, use_reloader=False)
