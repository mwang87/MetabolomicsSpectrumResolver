from flask import Flask

from metabolomics_spectrum_resolver import views


class CustomFlask(Flask):
    jinja_options = Flask.jinja_options.copy()
    jinja_options.update(dict(
        block_start_string='(%',
        block_end_string='%)',
        variable_start_string='((',
        variable_end_string='))',
        comment_start_string='(#',
        comment_end_string='#)'))


app = CustomFlask(__name__)
app.config.from_object(__name__)
app.register_blueprint(views.blueprint)

if __name__ == '__main__':
    app.run()
