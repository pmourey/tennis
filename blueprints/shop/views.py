from flask import render_template, request, flash, redirect, url_for, current_app
from blueprints.shop import shop_bp
from blueprints.shop.models import Racquet
from blueprints.shop import scraper as shop_scraper
from extensions import db


def _merge_payload(base: dict, extra: dict) -> dict:
    merged = dict(base or {})
    for key, value in (extra or {}).items():
        if value is not None and value != '':
            merged[key] = value
    return merged


def _upsert_racquet(payload: dict, mark_current: bool = False) -> str:
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
    ]
    for field in fields:
        value = payload.get(field)
        if value is not None and value != '':
            setattr(racquet, field, value)

    if mark_current:
        racquet.is_current = True

    if created:
        db.session.add(racquet)
        return 'created'
    return 'updated'


def _normalize_legacy_ounce_weights() -> int:
    """Convertit les poids historiques (oz) en grammes quand valeur manifestement en oz."""
    converted = 0
    for r in Racquet.query.all():
        if r.strung_weight is not None and r.strung_weight <= 30:
            r.strung_weight = round(r.strung_weight * shop_scraper.OZ_TO_G, 1)
            converted += 1
        if r.unstrung_weight is not None and r.unstrung_weight <= 30:
            r.unstrung_weight = round(r.unstrung_weight * shop_scraper.OZ_TO_G, 1)
            converted += 1
    return converted


@shop_bp.route('/')
def index():
    return redirect(url_for('shop.racquets'))


@shop_bp.route('/racquets')
def racquets():
    brand = request.args.get('brand', '')
    name_search = request.args.get('name_search', '')
    min_weight = request.args.get('min_weight', type=float)
    max_weight = request.args.get('max_weight', type=float)
    min_head = request.args.get('min_head', type=float)
    max_head = request.args.get('max_head', type=float)
    min_balance = request.args.get('min_balance', type=float)
    max_balance = request.args.get('max_balance', type=float)
    min_swingweight = request.args.get('min_swingweight', type=int)
    max_swingweight = request.args.get('max_swingweight', type=int)
    min_stiffness = request.args.get('min_stiffness', type=int)
    max_stiffness = request.args.get('max_stiffness', type=int)
    string_pattern = request.args.get('string_pattern', '')
    sort_by = request.args.get('sort_by', 'brand')
    current_only = request.args.get('current_only') == 'on'

    query = Racquet.query
    if current_only:
        query = query.filter(Racquet.is_current == True)
    if brand:
        query = query.filter(Racquet.brand.ilike(f'%{brand}%'))
    if name_search:
        query = query.filter(db.or_(Racquet.name.ilike(f'%{name_search}%'), Racquet.brand.ilike(f'%{name_search}%')))
    if min_weight:
        query = query.filter(Racquet.strung_weight >= min_weight)
    if max_weight:
        query = query.filter(Racquet.strung_weight <= max_weight)
    if min_head:
        query = query.filter(Racquet.head_size >= min_head)
    if max_head:
        query = query.filter(Racquet.head_size <= max_head)
    if min_balance:
        query = query.filter(Racquet.balance >= min_balance)
    if max_balance:
        query = query.filter(Racquet.balance <= max_balance)
    if min_swingweight:
        query = query.filter(Racquet.swingweight >= min_swingweight)
    if max_swingweight:
        query = query.filter(Racquet.swingweight <= max_swingweight)
    if min_stiffness:
        query = query.filter(Racquet.stiffness >= min_stiffness)
    if max_stiffness:
        query = query.filter(Racquet.stiffness <= max_stiffness)
    if string_pattern:
        query = query.filter(Racquet.string_pattern.ilike(f'%{string_pattern}%'))

    sort_map = {
        'brand': Racquet.brand,
        'name': Racquet.name,
        'weight': Racquet.strung_weight,
        'head_size': Racquet.head_size,
        'swingweight': Racquet.swingweight,
        'price': Racquet.price,
    }
    query = query.order_by(sort_map.get(sort_by, Racquet.brand))
    racquet_list = query.all()

    brands = [r[0] for r in db.session.query(Racquet.brand).distinct().order_by(Racquet.brand).all()]
    patterns = [r[0] for r in db.session.query(Racquet.string_pattern).distinct().filter(Racquet.string_pattern.isnot(None)).order_by(Racquet.string_pattern).all()]

    return render_template('shop/racquets.html', racquets=racquet_list, brands=brands, patterns=patterns, filters=request.args)


@shop_bp.route('/racquets/<int:racquet_id>')
def racquet_detail(racquet_id):
    racquet = Racquet.query.get_or_404(racquet_id)
    return render_template('shop/racquet_detail.html', racquet=racquet)


@shop_bp.route('/scrape', methods=['GET', 'POST'])
def scrape():
    import_enabled = current_app.config.get('SHOP_IMPORT_ENABLED', True)
    manufacturers = []
    try:
        manufacturers = shop_scraper.fetch_manufacturers()
    except Exception as exc:
        current_app.logger.warning('Impossible de charger les fabricants racquetfinder: %s', exc)

    if request.method == 'POST':
        if not import_enabled:
            flash('Import désactivé par configuration (SHOP_IMPORT_ENABLED=0).', 'warning')
            return redirect(url_for('shop.scrape'))

        manufacturer = request.form.get('manufacturer', '').strip()
        current_only = request.form.get('current_only') == 'on'
        normalize_legacy = request.form.get('normalize_legacy') == 'on'

        created = 0
        updated = 0
        skipped = 0
        parsed_with_head_size = 0

        try:
            if manufacturer:
                products = shop_scraper._collect_products_by_stiffness(
                    manufacturer=manufacturer,
                    current_only=current_only,
                )
                listing_rows = [shop_scraper.parse_product(p) for p in products]
            else:
                listing_rows = shop_scraper.scrape_all(current_only=current_only)

            for listing in listing_rows:
                pcode = str(listing.get('pcode') or '').strip()
                details = shop_scraper.scrape_racquet_by_pcode(pcode) if pcode else {}
                payload = _merge_payload(listing, details)

                if payload.get('head_size') is not None:
                    parsed_with_head_size += 1

                status = _upsert_racquet(payload, mark_current=current_only)
                if status == 'created':
                    created += 1
                elif status == 'updated':
                    updated += 1
                else:
                    skipped += 1

            converted = 0
            if normalize_legacy:
                converted = _normalize_legacy_ounce_weights()

            db.session.commit()
            flash(
                f'Import terminé: {created} créé(es), {updated} mis(es) à jour, {skipped} ignoré(es), '
                f'{parsed_with_head_size} avec head_size, {converted} poids converti(s) oz→g.',
                'success',
            )
            return redirect(url_for('shop.racquets'))
        except Exception as exc:
            db.session.rollback()
            current_app.logger.exception('Erreur import shop')
            flash(f'Erreur pendant le scraping: {exc}', 'error')
            return redirect(url_for('shop.scrape'))

    return render_template('shop/scrape.html', manufacturers=manufacturers)


@shop_bp.route('/racquets/<int:racquet_id>/delete', methods=['POST'])
def delete_racquet(racquet_id):
    racquet = Racquet.query.get_or_404(racquet_id)
    db.session.delete(racquet)
    db.session.commit()
    flash(f'Raquette {racquet} supprimée.', 'success')
    return redirect(url_for('shop.racquets'))
