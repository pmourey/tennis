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
        'release_year',
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
    release_year_from = request.args.get('release_year_from', type=int)
    release_year_to = request.args.get('release_year_to', type=int)

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
    # Filtre par année de sortie (seulement pour les raquettes dont release_year est renseigné)
    if release_year_from:
        query = query.filter(Racquet.release_year >= release_year_from)
    if release_year_to:
        query = query.filter(Racquet.release_year <= release_year_to)

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

    # Années disponibles pour le filtre (raquettes avec release_year renseigné)
    # ── Bornes physiques fixes (mêmes que racquet_detail.html) ───────────────
    from sqlalchemy import func as sqlfunc

    PHYS = {
        'weight':      (150, 400),
        'head':        (80,  140),
        'balance':     (-20, 20),
        'swingweight': (200, 430),
        'stiffness':   (40,  95),
    }

    year_row = db.session.query(
        sqlfunc.min(Racquet.release_year), sqlfunc.max(Racquet.release_year)
    ).filter(Racquet.release_year.isnot(None)).one()
    year_stats = {
        'min': int(year_row[0]) if year_row[0] else 2010,
        'max': int(year_row[1]) if year_row[1] else 2026,
    }


    def _db_range(field, lo, hi):
        row = db.session.query(sqlfunc.min(field), sqlfunc.max(field)).filter(
            field >= lo, field <= hi
        ).one()
        return (int(row[0]) if row[0] is not None else lo,
                int(row[1]) if row[1] is not None else hi)

    w_lo, w_hi   = _db_range(Racquet.strung_weight, *PHYS['weight'])
    h_lo, h_hi   = _db_range(Racquet.head_size,     *PHYS['head'])
    b_lo, b_hi   = _db_range(Racquet.balance,        *PHYS['balance'])
    sw_lo, sw_hi = _db_range(Racquet.swingweight,    *PHYS['swingweight'])
    st_lo, st_hi = _db_range(Racquet.stiffness,      *PHYS['stiffness'])

    range_stats = {
        'weight_min':      w_lo,  'weight_max':      w_hi,
        'head_min':        h_lo,  'head_max':        h_hi,
        'balance_min':     b_lo,  'balance_max':     b_hi,
        'swingweight_min': sw_lo, 'swingweight_max': sw_hi,
        'stiffness_min':   st_lo, 'stiffness_max':   st_hi,
    }

    return render_template('shop/racquets.html', racquets=racquet_list, brands=brands, patterns=patterns,
                           filters=request.args, range_stats=range_stats, year_stats=year_stats)


@shop_bp.route('/racquets/<int:racquet_id>')
def racquet_detail(racquet_id):
    racquet = Racquet.query.get_or_404(racquet_id)
    similar = _find_similar(racquet)

    # ── Bornes physiques absolues ──────────────────────────────────────────
    PHYS = dict(head=(85, 137), weight=(220, 400), swing=(200, 430), stiff=(40, 95), balance=(-15, 16))
    # Tolérances par défaut centrées sur la valeur de la raquette
    TOL  = dict(head=8, weight=20, swing=15, stiff=5, balance=3)

    def _init(key, val):
        lo, hi = PHYS[key]
        if val is None:
            return lo, hi, lo, hi          # pas de valeur → plage complète
        tol = TOL[key]
        return lo, hi, max(lo, val - tol), min(hi, val + tol)

    h_phys_lo, h_phys_hi, h_lo, h_hi     = _init('head',    int(racquet.head_size)    if racquet.head_size    else None)
    w_phys_lo, w_phys_hi, w_lo, w_hi     = _init('weight',  int(racquet.strung_weight) if racquet.strung_weight else None)
    sw_phys_lo, sw_phys_hi, sw_lo, sw_hi = _init('swing',   racquet.swingweight)
    st_phys_lo, st_phys_hi, st_lo, st_hi = _init('stiff',   racquet.stiffness)
    b_phys_lo,  b_phys_hi,  b_lo,  b_hi  = _init('balance', int(racquet.balance)       if racquet.balance is not None else None)

    slider_cfg = {
        'head':    (h_phys_lo,  h_phys_hi,  h_lo,  h_hi),
        'weight':  (w_phys_lo,  w_phys_hi,  w_lo,  w_hi),
        'swing':   (sw_phys_lo, sw_phys_hi, sw_lo, sw_hi),
        'stiff':   (st_phys_lo, st_phys_hi, st_lo, st_hi),
        'balance': (b_phys_lo,  b_phys_hi,  b_lo,  b_hi),
    }

    return render_template('shop/racquet_detail.html', racquet=racquet, similar=similar,
                           slider_cfg=slider_cfg)


def _find_similar(racquet: Racquet, limit: int = 6) -> list:
    """Trouve les raquettes avec des caractéristiques proches.

    Critères (pondérés) :
      - même string_pattern            → bonus fort
      - head_size   ± 5 sq.in          → requis si disponible
      - strung_weight ± 15 g           → requis si disponible
      - swingweight ± 15               → bonus
      - stiffness   ± 5                → bonus
    Priorité aux raquettes is_current=True.
    """
    q = Racquet.query.filter(Racquet.id != racquet.id)

    # Filtres souples sur les métriques disponibles
    filters = []
    if racquet.head_size:
        filters.append(
            db.and_(Racquet.head_size >= racquet.head_size - 5,
                    Racquet.head_size <= racquet.head_size + 5)
        )
    if racquet.strung_weight:
        filters.append(
            db.and_(Racquet.strung_weight >= racquet.strung_weight - 15,
                    Racquet.strung_weight <= racquet.strung_weight + 15)
        )
    if filters:
        q = q.filter(db.and_(*filters))

    # Récupérer les candidates (préférer les actuelles)
    candidates = q.order_by(
        Racquet.is_current.desc(),
        Racquet.brand,
    ).limit(100).all()

    # Scoring fin
    def score(r):
        s = 0
        if racquet.string_pattern and r.string_pattern == racquet.string_pattern:
            s += 4
        if racquet.swingweight and r.swingweight:
            if abs(r.swingweight - racquet.swingweight) <= 15:
                s += 3
        if racquet.stiffness and r.stiffness:
            if abs(r.stiffness - racquet.stiffness) <= 5:
                s += 2
        if racquet.balance and r.balance:
            if abs(r.balance - racquet.balance) <= 3:
                s += 2
        if r.is_current:
            s += 1
        return s

    candidates.sort(key=score, reverse=True)
    return candidates[:limit]


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

    return render_template('shop/scrape.html', manufacturers=manufacturers, import_enabled=import_enabled)


@shop_bp.route('/racquets/<int:racquet_id>/delete', methods=['POST'])
def delete_racquet(racquet_id):
    racquet = Racquet.query.get_or_404(racquet_id)
    db.session.delete(racquet)
    db.session.commit()
    flash(f'Raquette {racquet} supprimée.', 'success')
    return redirect(url_for('shop.racquets'))


@shop_bp.route('/racquets/similar_ajax')
def similar_ajax():
    from flask import jsonify
    import math

    # Plages min/max directes
    min_head    = request.args.get('min_head',    type=float)
    max_head    = request.args.get('max_head',    type=float)
    min_weight  = request.args.get('min_weight',  type=float)
    max_weight  = request.args.get('max_weight',  type=float)
    min_swing   = request.args.get('min_swing',   type=int)
    max_swing   = request.args.get('max_swing',   type=int)
    min_stiff   = request.args.get('min_stiff',   type=int)
    max_stiff   = request.args.get('max_stiff',   type=int)
    min_balance = request.args.get('min_balance', type=float)
    max_balance = request.args.get('max_balance', type=float)
    exclude_id  = request.args.get('exclude_id',  type=int)
    current_only = request.args.get('current_only') == '1'
    limit       = request.args.get('limit', 24, type=int)

    q = Racquet.query
    if exclude_id:
        q = q.filter(Racquet.id != exclude_id)
    if current_only:
        q = q.filter(db.or_(Racquet.is_current == True,
                             Racquet.release_year >= 2015))

    if min_head    is not None: q = q.filter(Racquet.head_size     >= min_head)
    if max_head    is not None: q = q.filter(Racquet.head_size     <= max_head)
    if min_weight  is not None: q = q.filter(Racquet.strung_weight >= min_weight)
    if max_weight  is not None: q = q.filter(Racquet.strung_weight <= max_weight)
    if min_swing   is not None: q = q.filter(Racquet.swingweight   >= min_swing)
    if max_swing   is not None: q = q.filter(Racquet.swingweight   <= max_swing)
    if min_stiff   is not None: q = q.filter(Racquet.stiffness     >= min_stiff)
    if max_stiff   is not None: q = q.filter(Racquet.stiffness     <= max_stiff)
    if min_balance is not None: q = q.filter(Racquet.balance       >= min_balance)
    if max_balance is not None: q = q.filter(Racquet.balance       <= max_balance)

    candidates = q.limit(300).all()

    # ── Référence : raquette de base  ─────────────────────────────────────
    ref = Racquet.query.get(exclude_id) if exclude_id else None

    # ── Paramètres de chaque dimension : (champ_candidat, val_ref, span, poids) ──
    # span = largeur de la plage active (pour normalisation)
    def _span(lo, hi): return (hi - lo) if lo is not None and hi is not None and hi > lo else None

    dims = [
        ('head_size',     (min_head    + max_head)    / 2 if min_head    is not None and max_head    is not None else (ref.head_size    if ref and ref.head_size    else None), _span(min_head,    max_head),    3.0),
        ('strung_weight', (min_weight  + max_weight)  / 2 if min_weight  is not None and max_weight  is not None else (ref.strung_weight if ref and ref.strung_weight else None), _span(min_weight,  max_weight),  2.5),
        ('swingweight',   (min_swing   + max_swing)   / 2 if min_swing   is not None and max_swing   is not None else (ref.swingweight  if ref and ref.swingweight  else None), _span(min_swing,   max_swing),   3.0),
        ('stiffness',     (min_stiff   + max_stiff)   / 2 if min_stiff   is not None and max_stiff   is not None else (ref.stiffness    if ref and ref.stiffness    else None), _span(min_stiff,   max_stiff),   2.0),
        ('balance',       (min_balance + max_balance) / 2 if min_balance is not None and max_balance is not None else (ref.balance      if ref and ref.balance is not None else None), _span(min_balance, max_balance), 1.5),
    ]

    def _distance(r):
        """Distance normalisée multi-critères. Inférieure = plus proche."""
        total_w = 0.0
        dist    = 0.0
        for field, ref_val, span, w in dims:
            r_val = getattr(r, field)
            if ref_val is None or r_val is None:
                continue
            norm = span if span else 20.0          # normalisation par la plage active
            d = abs(float(r_val) - float(ref_val)) / norm
            dist    += d * w
            total_w += w
        if total_w == 0:
            return float('inf')
        base = dist / total_w
        # Légère récompense pour les modèles actuels
        if r.is_current:
            base -= 0.05
        return base

    candidates.sort(key=_distance)

    results = []
    for r in candidates[:limit]:
        d = _distance(r)
        results.append({
            'id':           r.id,
            'brand':        r.brand,
            'name':         r.name,
            'is_current':   r.is_current,
            'release_year': r.release_year,
            'head_size':    int(r.head_size)     if r.head_size     else None,
            'strung_weight':int(r.strung_weight) if r.strung_weight else None,
            'swingweight':  r.swingweight,
            'stiffness':    r.stiffness,
            'balance':      r.balance,
            'string_pattern': r.string_pattern,
            'distance':     round(d, 3),
            'url':          url_for('shop.racquet_detail', racquet_id=r.id),
            'image_local':  r.image_local,
            'image_url':    r.image_url,
        })
    return jsonify(results)


def _compute_recommendations(form):
    level = form.get('level', 'loisir')
    age_group = form.get('age_group', 'adulte')
    style = form.get('style', 'polyvalent')
    injuries = form.get('injuries', 'none')
    priority = form.get('priority', 'confort')
    casseur = form.get('casseur', 'rarement')
    morphologie = form.get('morphologie', 'moyen')

    # Head size (sq.in)
    if age_group == 'enfant' or level == 'debutant':
        head_min, head_max = 104, 115
        head_label = 'Grand tamis (104–115 sq.in) — zone de frappe maximale, sweet spot large'
    elif level == 'loisir':
        head_min, head_max = 100, 108
        head_label = 'Moyen-grand tamis (100–108 sq.in) — confort + puissance'
    elif level == 'intermediaire':
        head_min, head_max = 95, 102
        head_label = 'Tamis moyen (95–102 sq.in) — équilibre précision/puissance'
    else:  # competiteur
        head_min, head_max = 85, 98
        head_label = 'Petit-moyen tamis (85–98 sq.in) — contrôle et précision maximaux'

    # Weight (g)
    if age_group == 'enfant':
        weight_min, weight_max = 200, 260
    elif level == 'debutant':
        weight_min, weight_max = 250, 285
    elif level == 'loisir':
        weight_min, weight_max = 265, 295
    elif level == 'intermediaire':
        weight_min, weight_max = 275, 310
    else:  # competiteur
        weight_min, weight_max = 295, 335

    if morphologie == 'petit':
        weight_max = max(weight_min + 10, weight_max - 15)
    elif morphologie == 'grand':
        weight_min += 10

    if injuries in ('tennis_elbow', 'poignet', 'epaule') and weight_max > 295:
        weight_max = 295

    # Balance
    if style == 'attaquant':
        balance_label = '⬅ Équilibre en manche (tête légère, HL) — maniabilité & toucher au filet'
        balance_dir = 'HL'
    elif style == 'defenseur':
        balance_label = '➡ Équilibre en tête (HH) — puissance depuis le fond de court'
        balance_dir = 'HH'
    else:
        balance_label = '↔ Équilibre neutre — polyvalence tous styles'
        balance_dir = 'neutre'

    # Stiffness (RA)
    if injuries in ('tennis_elbow', 'poignet', 'epaule') or level == 'debutant':
        ra_min, ra_max = 55, 63
        ra_label = 'Raquette souple (55–63 RA) — protection articulations, absorption des chocs'
    elif level == 'loisir':
        ra_min, ra_max = 60, 67
        ra_label = 'Semi-rigide (60–67 RA) — compromis confort / contrôle'
    elif level == 'intermediaire':
        ra_min, ra_max = 62, 70
        ra_label = 'Semi-rigide à rigide (62–70 RA) — bon contrôle avec un peu de confort'
    else:  # competiteur
        ra_min, ra_max = 65, 80
        ra_label = 'Rigide (65+ RA) — stabilité maximale à l\'impact'

    # Cordage
    if injuries in ('tennis_elbow', 'poignet', 'epaule'):
        stype = 'Multifilament ou Boyau naturel'
        sgauge = '1.24 – 1.28 mm'
        stension = 'Basse (−2 kg vs médiane fabricant)'
        srationale = ('⚕️ Protection prioritaire des articulations — absorption maximale des vibrations. '
                      'Éviter absolument les monofilaments. Prétendre le cordage pour améliorer la durée de vie.')
    elif casseur == 'souvent':
        stype = 'Monofilament polyester (co-poly)'
        sgauge = '1.20 – 1.27 mm'
        stension = 'Médiane (−2 kg vs multifilament)'
        srationale = ('🔴 Gros casseur : résistance maximale + excellente prise d\'effets. '
                      'Baisser la tension de 2 kg. Cordage structuré (pentagonal/hexagonal) pour encore plus d\'effets.')
    elif casseur == 'parfois' and level == 'competiteur':
        stype = 'Hybride (monofilament en montants / multifilament en travers)'
        sgauge = '1.22 – 1.28 mm'
        stension = 'Médiane'
        srationale = ('🟠 Compromis résistance/jouabilité : les montants mono donnent contrôle et lift, '
                      'les travers multi apportent confort et puissance. Méthode Federer inversée pour les lifters.')
    elif priority == 'effets':
        stype = 'Monofilament texturé ou Polyester structuré (polyédrique)'
        sgauge = '1.20 – 1.25 mm'
        stension = 'Médiane à haute'
        srationale = ('🌀 Maximise le lift et le slice. La jauge fine + structure angulaire mordent mieux '
                      'sur la balle. Idéal pour les lifteurs et joueurs à effets marqués.')
    elif priority == 'puissance' or level == 'debutant':
        stype = 'Multifilament ou Nylon à guipage'
        sgauge = '1.25 – 1.30 mm'
        stension = 'Basse à médiane'
        srationale = ('⚡ Effet trampoline pour plus de vitesse de balle. Excellente jouabilité et confort. '
                      'Alternative économique au boyau pour les débutants et loisirs.')
    elif priority == 'controle':
        stype = 'Monofilament ou Multifilament renforcé'
        sgauge = '1.27 – 1.32 mm'
        stension = 'Médiane à haute'
        srationale = ('🎯 Jauge épaisse = meilleur contrôle de trajectoire. Tension plus haute pour '
                      'réduire l\'élasticité et garder la balle dans le court.')
    else:  # confort
        stype = 'Multifilament'
        sgauge = '1.25 – 1.30 mm'
        stension = 'Médiane'
        srationale = ('✅ Meilleur compromis jouabilité, confort et durabilité. Proche du boyau naturel '
                      'sans le prix prohibitif. À changer tous les 6 mois même non cassé.')

    return {
        'head_min': head_min, 'head_max': head_max, 'head_label': head_label,
        'weight_min': weight_min, 'weight_max': weight_max,
        'balance_dir': balance_dir, 'balance_label': balance_label,
        'ra_min': ra_min, 'ra_max': ra_max, 'ra_label': ra_label,
        'string_type': stype, 'string_gauge': sgauge,
        'string_tension': stension, 'string_rationale': srationale,
    }


@shop_bp.route('/racquets/selector', methods=['GET', 'POST'])
def racquet_selector():
    recs = None
    matching = []
    form = {}
    if request.method == 'POST':
        form = request.form.to_dict()
        recs = _compute_recommendations(form)
        q = Racquet.query
        q = q.filter(Racquet.head_size >= recs['head_min'], Racquet.head_size <= recs['head_max'])
        q = q.filter(Racquet.strung_weight >= recs['weight_min'], Racquet.strung_weight <= recs['weight_max'])
        q = q.filter(db.or_(
            Racquet.stiffness.is_(None),
            db.and_(Racquet.stiffness >= recs['ra_min'], Racquet.stiffness <= recs['ra_max'])
        ))
        if recs['balance_dir'] == 'HL':
            q = q.filter(db.or_(Racquet.balance.is_(None), Racquet.balance <= 0))
        elif recs['balance_dir'] == 'HH':
            q = q.filter(db.or_(Racquet.balance.is_(None), Racquet.balance >= 0))
        matching = q.order_by(Racquet.is_current.desc(), Racquet.brand).limit(12).all()

    return render_template('shop/racquet_selector.html', recs=recs, matching=matching, form=form)


@shop_bp.route('/diagnose/<pcode>')
def diagnose_pcode(pcode):
    """Route de diagnostic : vérifie ce que le scraper récupère pour un pcode donné."""
    try:
        result = shop_scraper.diagnose_head_size(pcode.upper())
    except Exception as exc:
        result = {'error': str(exc)}
    from flask import jsonify
    return jsonify(result)


