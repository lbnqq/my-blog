import os
import subprocess
import sys
from tempfile import TemporaryDirectory
from pathlib import Path

from django.test import SimpleTestCase


SCRIPT_PATH = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "movie-blog-cli" / "scripts" / "run_blog.py"


def make_fake_project(tmp_path):
    project = tmp_path / "movie-blog"
    command_dir = project / "apps" / "blog" / "management" / "commands"
    command_dir.mkdir(parents=True)
    (project / "manage.py").write_text(
        "import os\n"
        "import sys\n"
        "print('cwd=' + os.getcwd())\n"
        "print('use_sqlite=' + os.environ.get('USE_SQLITE', ''))\n"
        "print('args=' + repr(sys.argv[1:]))\n"
        "if 'fail' in sys.argv:\n"
        "    sys.exit(7)\n",
        encoding="utf-8",
    )
    (command_dir / "blog.py").write_text("# fake blog command\n", encoding="utf-8")
    return project


def run_script(args, env):
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


class MovieBlogSkillScriptTests(SimpleTestCase):
    def test_run_blog_executes_manage_blog_from_env_root(self):
        with TemporaryDirectory() as tmpdir:
            project = make_fake_project(Path(tmpdir))
            env = os.environ.copy()
            env["MOVIE_BLOG_ROOT"] = str(project)

            result = run_script(["home"], env)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"cwd={project}", result.stdout)
        self.assertIn("args=['blog', 'home']", result.stdout)

    def test_run_blog_sets_sqlite_env_when_requested(self):
        with TemporaryDirectory() as tmpdir:
            project = make_fake_project(Path(tmpdir))
            env = os.environ.copy()
            env["MOVIE_BLOG_ROOT"] = str(project)
            env.pop("USE_SQLITE", None)

            result = run_script(["movies", "search", "大话西游", "--sqlite"], env)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("use_sqlite=1", result.stdout)
        self.assertIn("args=['blog', 'movies', 'search', '大话西游']", result.stdout)

    def test_run_blog_returns_child_exit_code(self):
        with TemporaryDirectory() as tmpdir:
            project = make_fake_project(Path(tmpdir))
            env = os.environ.copy()
            env["MOVIE_BLOG_ROOT"] = str(project)

            result = run_script(["fail"], env)

        self.assertEqual(result.returncode, 7)
