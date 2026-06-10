#!/usr/bin/env python
import os
import subprocess
import sys
from pathlib import Path


BLOG_COMMAND_PATH = Path("apps") / "blog" / "management" / "commands" / "blog.py"


def is_project_root(path):
    return (path / "manage.py").is_file() and (path / BLOG_COMMAND_PATH).is_file()


def walk_for_project_root(start):
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for path in (current, *current.parents):
        if is_project_root(path):
            return path
    return None


def find_project_root():
    env_root = os.environ.get("MOVIE_BLOG_ROOT")
    if env_root:
        path = Path(env_root)
        if is_project_root(path):
            return path.resolve()
        raise SystemExit(f"MOVIE_BLOG_ROOT is not a movie blog project root: {path}")

    for start in (Path.cwd(), Path(__file__).resolve()):
        root = walk_for_project_root(start)
        if root is not None:
            return root

    raise SystemExit(
        "Cannot find movie blog project root. Run from the project, or set MOVIE_BLOG_ROOT."
    )


def split_args(argv):
    command_args = []
    use_sqlite = False
    for arg in argv:
        if arg == "--sqlite":
            use_sqlite = True
        else:
            command_args.append(arg)
    return command_args, use_sqlite


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    command_args, use_sqlite = split_args(argv)
    if not command_args:
        print(
            "Usage: run_blog.py <blog-command> [args...] [--sqlite]",
            file=sys.stderr,
        )
        return 2

    project_root = find_project_root()
    env = os.environ.copy()
    if use_sqlite:
        env["USE_SQLITE"] = "1"

    result = subprocess.run(
        [sys.executable, "manage.py", "blog", *command_args],
        cwd=project_root,
        env=env,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
