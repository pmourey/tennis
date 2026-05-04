"""
Import batch du catalogue raquettes depuis racquetfinder.com.
Appelle directement la logique de scraping sans passer par HTTP,
pour éviter le conflit de connexions SQLite (database is locked).

Usage:
    python3 run_shop_full_import.py
    python3 run_shop_full_import.py --manufacturer Wilson
    python3 run_shop_full_import.py --no-normalize
"""
import sys
import time
import argparse

from app import create_app
from blueprints.shop.models import Racquet
from blueprints.shop import scraper as shop_scraper
from extensions import db


def _merge_payload(base: dict, extra: dict) -> dict:
    merged = dict(base or {})
    for key, value in (extra or {}).items():
        if value is not None and value != '':
            merged[key] = value
    return merged


def _upsert_racquet(payload: dict) -> str:
    brand = (payload.get('brand') or 'Unknown').strip()
    name = (payload.get('name') or '').strip()
    if not name:
        return 'skipped'

    racquet = Racquet.query.filter_by(brand=brand, name=name).first()
    created = racquet is None
    if created:
        racquet = Racquet(brand=brand, name=name)

    fields = [
        'head_size', 'length', 'strung_weight', 'unstrung_weight',
        'balance', 'swingweight', 'stiffness', 'beam_width',
        'string_pattern', 'string_tension', 'price', 'url',
        'image_url', 'image_local', 'player_type', 'composition', 'color',
        'pcode',
    ]
    for field in fields:
        value = payload.get(field)
        if value is not None and value != '':
            setattr(racquet, field, value)

    if created:
        db.session.add(racquet)
        return 'created'
    return 'updated'


def _normalize_legacy_ounce_weights() -> int:
    """Convertit les poids historiques (oz) en grammes quand valeur ≤ 30."""
    converted = 0
    for r in Racquet.query.all():
        if r.strung_weight is not None and r.strung_weight <= 30:
            r.strung_weight = round(r.strung_weight * shop_scraper.OZ_TO_G, 1)
            converted += 1
        if r.unstrung_weight is not None and r.unstrung_weight <= 30:
            r.unstrung_weight = round(r.unstrung_weight * shop_scraper.OZ_TO_G, 1)
            converted += 1
    return converted


def run_import(manufacturer='', current_only=False, normalize_legacy=True, commit_every=50):
    app = create_app()

    with app.app_context():
        before_total = db.session.query(Racquet).count()
        before_head = db.session.query(Racquet).filter(Racquet.head_size.isnot(None)).count()
        print(f"DB avant: total={before_total}, head_size_not_null={before_head}")

    start = time.time()
    created = updated = skipped = parsed_with_head_size = 0

    with app.app_context():
        try:
            # --- Collecte du listing ---
            if manufacturer:
                print(f"Scraping fabricant: {manufacturer}")
                products = shop_scraper._collect_products_by_stiffness(
                    manufacturer=manufacturer, current_only=current_only
                )
                listing_rows = [shop_scraper.parse_product(p) for p in products]
            else:
                print("Scraping TOUS les fabricants (mode batch)...")
                listing_rows = shop_scraper.scrape_all(
                    current_only=current_only,
                    progress_callback=lambda i, n, label: print(f"  [{i+1}/{n}] {label}"),
                )

            total = len(listing_rows)
            print(f"\n{total} raquettes trouvées dans le listing. Scraping des détails...")

            for idx, listing in enumerate(listing_rows, 1):
                pcode = str(listing.get('pcode') or '').strip()
                details = {}
                if pcode:
                    details = shop_scraper.scrape_racquet_by_pcode(pcode)

                payload = _merge_payload(listing, details)

                if payload.get('head_size') is not None:
                    parsed_with_head_size += 1

                status = _upsert_racquet(payload)
                if status == 'created':
                    created += 1
                elif status == 'updated':
                    updated += 1
                else:
                    skipped += 1

                # Commit partiel pour éviter une transaction trop longue
                if idx % commit_every == 0:
                    db.session.commit()
                    elapsed = time.time() - start
                    print(f"  [{idx}/{total}] +{created}c +{updated}u  {elapsed:.0f}s", flush=True)

            # Normalisation poids oz → g
            converted = 0
            if normalize_legacy:
                converted = _normalize_legacy_ounce_weights()

            db.session.commit()
            print(f"\n✓ Import terminé: {created} créé(es), {updated} mis(es) à jour, "
                  f"{skipped} ignoré(es), {parsed_with_head_size} avec head_size, "
                  f"{converted} poids converti(s) oz→g.")

        except Exception as exc:
            db.session.rollback()
            print(f"\n✗ Erreur import: {exc}", file=sys.stderr)
            raise

    with app.app_context():
        after_total = db.session.query(Racquet).count()
        after_head = db.session.query(Racquet).filter(Racquet.head_size.isnot(None)).count()
        low_weight = db.session.query(Racquet).filter(
            Racquet.strung_weight.isnot(None),
            Racquet.strung_weight <= 30,
        ).count()
        min_weight = db.session.query(db.func.min(Racquet.strung_weight)).scalar()
        max_weight = db.session.query(db.func.max(Racquet.strung_weight)).scalar()
        print(f"DB après: total={after_total}, head_size_not_null={after_head}")
        print(f"Poids: <=30g_count={low_weight}, min={min_weight}, max={max_weight}")

    print(f"Durée totale: {time.time() - start:.1f}s")


def main():
    parser = argparse.ArgumentParser(description='Import batch catalogue raquettes')
    parser.add_argument('--manufacturer', default='', help='Fabricant spécifique (vide = tous)')
    parser.add_argument('--current-only', action='store_true', help='Raquettes actuelles seulement')
    parser.add_argument('--no-normalize', action='store_true', help='Ne pas normaliser les poids oz→g')
    parser.add_argument('--commit-every', type=int, default=50, help='Commit partiel tous les N enregistrements')
    args = parser.parse_args()

    run_import(
        manufacturer=args.manufacturer,
        current_only=args.current_only,
        normalize_legacy=not args.no_normalize,
        commit_every=args.commit_every,
    )


if __name__ == '__main__':
    main()

