import argparse
import json

from . import config
from .pipeline import attach_images, generate_post
from .publisher import publish_due
from .store import Store


def main(argv=None):
    ap = argparse.ArgumentParser(prog="swarm")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="Corre el enjambre y deja un post en la cola")
    g.add_argument("--topic")
    sub.add_parser("list")
    s = sub.add_parser("show")
    s.add_argument("id", type=int)
    r = sub.add_parser("render", help="Genera imágenes con FLUX para un post en needs_assets")
    r.add_argument("id", type=int)
    i = sub.add_parser("images", help="Adjunta URLs públicas de imágenes a un post")
    i.add_argument("id", type=int)
    i.add_argument("urls", nargs="+")
    a = sub.add_parser("approve")
    a.add_argument("id", type=int)
    a.add_argument("--at", help="ISO UTC, ej. 2026-10-09T14:00:00+00:00")
    sub.add_parser("publish", help="Publica los aprobados que ya tocan")
    args = ap.parse_args(argv)

    store = Store()
    if args.cmd == "generate":
        from .llm import LLM

        provider = storage = None
        if config.BFL_API_KEY:
            from .images import BFLProvider, make_storage

            provider, storage = BFLProvider(), make_storage()
        generate_post(LLM(), store, args.topic, image_provider=provider, storage=storage)
    elif args.cmd == "render":
        from .images import BFLProvider, make_storage, render_images

        post = store.get(args.id)
        urls = render_images(post["payload"]["visual"], BFLProvider(), make_storage(), f"post{args.id}")
        if urls:
            attach_images(store, args.id, urls)
        else:
            print("Imágenes guardadas en data/images, pero sin URL pública: configura IMAGE_STORAGE=cloudinary.")
    elif args.cmd == "list":
        for r in store.list():
            print(r)
    elif args.cmd == "show":
        print(json.dumps(store.get(args.id), ensure_ascii=False, indent=2))
    elif args.cmd == "images":
        attach_images(store, args.id, args.urls)
    elif args.cmd == "approve":
        if args.at:
            store.db.execute("UPDATE posts SET scheduled_at=? WHERE id=?", (args.at, args.id))
        store.set_status(args.id, "approved")
    elif args.cmd == "publish":
        print(f"DRY_RUN={config.DRY_RUN}")
        print(f"publicados: {publish_due(store)}")


if __name__ == "__main__":
    main()
