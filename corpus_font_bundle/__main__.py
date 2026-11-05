import argparse
import json
import sys

from .api import buildBundle, verifyBundle
from .demo import human, run
from .errors import BundleError
from .files import read_regular, recoverStage
from .validation import parse_json


def main(argv=None):
    parser = argparse.ArgumentParser(prog="corpus-font-bundle", description="Corpus-specific font replay, development 0.1.0")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="offline synthetic differential demo")
    demo.add_argument("--assert", dest="assertions", action="store_true")
    demo.add_argument("--json", action="store_true")
    build = sub.add_parser("build")
    build.add_argument("--font", required=True)
    build.add_argument("--corpus-file", required=True)
    build.add_argument("--cases-file", required=True)
    build.add_argument("--destination", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--font", required=True)
    verify.add_argument("--bundle", required=True)
    recover = sub.add_parser("recover")
    recover.add_argument("--stage", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            result = run(args.assertions)
            print(json.dumps(result, sort_keys=True, ensure_ascii=False) if args.json else human(result))
            return 0 if result["ok"] else 1
        if args.command == "recover":
            result = recoverStage(args.stage)
        elif args.command == "build":
            try:
                corpus = read_regular(args.corpus_file, 65536).decode("utf-8", "strict")
            except UnicodeError:
                raise BundleError("INVALID_TEXT") from None
            cases = parse_json(read_regular(args.cases_file, 128 * 1024))
            manifest = buildBundle(args.font, corpus, cases, {"destination": args.destination})
            result = {"artifacts": manifest["artifacts"], "cases": len(manifest["cases"])}
        else:
            manifest = verifyBundle(args.font, args.bundle)
            result = {"artifacts": manifest["artifacts"], "cases": len(manifest["cases"])}
        print(json.dumps({"ok": True, **result}, sort_keys=True))
        return 0
    except BundleError as error:
        print(json.dumps({"ok": False, "error": error.as_dict()}, sort_keys=True), file=sys.stderr)
        return 1
    except OSError:
        print('{"error":{"code":"IO_ERROR"},"ok":false}', file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
