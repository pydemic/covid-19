import warnings

from invoke import task


@task
def calculator(ctx):
    warnings.warn("Please use the inv run task.")
    run(ctx)


@task
def run(ctx):
    ctx.run("streamlit run covid/ui/calc.py")


@task
def calculator_production(ctx):
    import os

    if os.environ.get("COVID_PERFORM_FIRST_SETUP", "false") == "true":
        repos = {
            "pt_BR.UTF-8": "https://github.com/caiosba/streamlit.git",
            "en_US.UTF-8": "https://github.com/streamlit/streamlit.git",
        }

        lang = os.environ.get("COVID_LANG", "en_US.UTF-8")
        repo = repos[lang]

        path = "/usr/local/lib/python3.8/site-packages/streamlit"

        ctx.run(f"cd {path} && git remote add {lang} {repo}")
        ctx.run(f"cd {path} && git fetch {lang}")
        ctx.run(f"cd {path} && git checkout {lang}/master")
        ctx.run(f"cd {path}/frontend && yarn install")
        ctx.run(f"cd {path} && make frontend")

    ctx.run("inv calculator")


@task
def compilemessages(ctx):
    ctx.run("pybabel compile -d covid/locale")


@task
def makemessages(ctx):
    ctx.run("pybabel extract -o covid/locale/messages.pot covid")
    ctx.run("pybabel update -i covid/locale/messages.pot -d covid/locale")


@task
def i18n(ctx):
    makemessages(ctx)
    compilemessages(ctx)


@task
def test(ctx):
    ctx.run("black --check .")
    ctx.run("pycodestyle")
    ctx.run("coverage run -m pytest")
    ctx.run("coverage report --show-missing")
