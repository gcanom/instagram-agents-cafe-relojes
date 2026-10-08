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
    n = sub.add_parser("ingest", help="Encola un post ya redactado (JSON con plan/research/copy/review/visual)")
    n.add_argument("file")
    n.add_argument("--render", action="store_true", help="Genera imágenes con FLUX tras encolar")
    r = sub.add_parser("render", help="Genera imágenes con FLUX para un post en needs_assets")
    r.add_argument("id", type=int)
    i = sub.add_parser("images", help="Adjunta URLs públicas de imágenes a un post")
    i.add_argument("id", type=int)
    i.add_argument("urls", nargs="+")
    sub.add_parser("review", help="Muestra los posts pendientes de aprobación (texto, imágenes, notas del revisor)")
    j = sub.add_parser("reject")
    j.add_argument("id", type=int)
    a = sub.add_parser("approve")
    a.add_argument("id", type=int)
    a.add_argument("--at", help="ISO UTC, ej. 2026-10-09T14:00:00+00:00")
    sub.add_parser("publish", help="Publica los aprobados que ya tocan")
    sub.add_parser("run", help="Ciclo para cron: genera un post (si no hay ya en espera) y publica lo aprobado")
    args = ap.parse_args(argv)

    store = Store()
    if args.cmd == "generate":
        from .llm import make_llm

        provider = storage = None
        if config.BFL_API_KEY:
            from .images import BFLProvider, make_storage

            provider, storage = BFLProvider(), make_storage()
        generate_post(make_llm(), store, args.topic, image_provider=provider, storage=storage)
    elif args.cmd == "ingest":
        payload = json.load(open(args.file))
        payload.setdefault("image_urls", [])
        post_id = store.add("needs_assets", payload)
        print(f"post {post_id} encolado")
        if args.render:
            from .images import BFLProvider, make_storage, render_images

            urls = render_images(payload["visual"], BFLProvider(), make_storage(), f"post{post_id}")
            if urls:
                attach_images(store, post_id, urls)
                print(f"estado: {store.get(post_id)['status']}")
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
    elif args.cmd == "review":
        pending = store.list("pending_approval")
        for row in pending:
            post = store.get(row["id"])["payload"]
            copy, review = post["copy"], post.get("review", {})
            print(f"\n=== POST {row['id']} · {post['plan'].get('topic')} · {post['plan'].get('format')} ===")
            for n, slide in enumerate(copy.get("slides", []), 1):
                print(f" {n}. {slide}")
            print(f"\nCAPTION:\n{copy.get('caption')}\n{' '.join(copy.get('hashtags', []))}")
            print("\nIMÁGENES:", *post.get("image_urls", []), sep="\n  ")
            for note in review.get("suggestions", []) + review.get("blocking", []):
                print(f"  ⚠ {note}")
            print(f"\n→ swarm approve {row['id']} [--at ISO-UTC]   |   swarm reject {row['id']}")
        if not pending:
            print("Nada pendiente.")
    elif args.cmd == "reject":
        store.set_status(args.id, "rejected", "rechazado manualmente")
    elif args.cmd == "images":
        attach_images(store, args.id, args.urls)
    elif args.cmd == "approve":
        if args.at:
            store.db.execute("UPDATE posts SET scheduled_at=? WHERE id=?", (args.at, args.id))
        store.set_status(args.id, "approved")
    elif args.cmd == "run":
        from .llm import make_llm

        waiting = store.list("pending_approval") + store.list("approved") + store.list("needs_assets")
        if len(waiting) < 3:  # no acumular borradores sin revisar
            provider = storage = None
            if config.BFL_API_KEY:
                from .images import BFLProvider, make_storage

                provider, storage = BFLProvider(), make_storage()
            generate_post(make_llm(), store, image_provider=provider, storage=storage)
        else:
            print(f"{len(waiting)} posts en espera; no genero más")
        print(f"publicados: {publish_due(store)}")
    elif args.cmd == "publish":
        print(f"DRY_RUN={config.DRY_RUN}")
        print(f"publicados: {publish_due(store)}")


if __name__ == "__main__":
    main()
