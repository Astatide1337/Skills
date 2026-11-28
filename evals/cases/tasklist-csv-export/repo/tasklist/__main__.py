import sys

from tasklist import store


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: tasklist add TITLE | list | done ID", file=sys.stderr)
        return 2
    command, *rest = argv
    if command == "add":
        task = store.add(" ".join(rest))
        print(f"added {task['id']}")
    elif command == "list":
        for task in store.load():
            mark = "x" if task["done"] else " "
            print(f"[{mark}] {task['id']}. {task['title']}")
    elif command == "done":
        store.mark_done(int(rest[0]))
    else:
        print(f"unknown command: {command}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
