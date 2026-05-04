# Source Generated with Decompyle++
# File: views.cpython-310.pyc (Python 3.10)

from flask import render_template, request, flash, redirect, url_for, current_app
from blueprints.shop import shop_bp
from blueprints.shop.models import Racquet
from extensions import db

def index():
    return redirect(url_for('shop.racquets'))

index = shop_bp.route('/')(index)

def racquets():
    brand = request.args.get('brand', '')
    name_search = request.args.get('name_search', '')
    min_weight = request.args.get('min_weight', float, **('type',))
    max_weight = request.args.get('max_weight', float, **('type',))
    min_head = request.args.get('min_head', float, **('type',))
    max_head = request.args.get('max_head', float, **('type',))
    min_balance = request.args.get('min_balance', float, **('type',))
    max_balance = request.args.get('max_balance', float, **('type',))
    min_swingweight = request.args.get('min_swingweight', int, **('type',))
    max_swingweight = request.args.get('max_swingweight', int, **('type',))
    min_stiffness = request.args.get('min_stiffness', int, **('type',))
    max_stiffness = request.args.get('max_stiffness', int, **('type',))
    string_pattern = request.args.get('string_pattern', '')
    sort_by = request.args.get('sort_by', 'brand')
    current_only = request.args.get('current_only') == 'on'
    query = Racquet.query
    if current_only:
        query = query.filter(Racquet.is_current == True)
    if brand:
        query = query.filter(Racquet.brand.ilike(f'''%{brand}%'''))
    if name_search:
        query = query.filter(db.or_(Racquet.name.ilike(f'''%{name_search}%'''), Racquet.brand.ilike(f'''%{name_search}%''')))
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
        query = query.filter(Racquet.string_pattern.ilike(f'''%{string_pattern}%'''))
    sort_map = {
        'brand': Racquet.brand,
        'name': Racquet.name,
        'weight': Racquet.strung_weight,
        'head_size': Racquet.head_size,
        'swingweight': Racquet.swingweight,
        'price': Racquet.price }
    query = query.order_by(sort_map.get(sort_by, Racquet.brand))
    racquet_list = query.all()
    brands = (lambda .0: [ r[0] for r in .0 ])(db.session.query(Racquet.brand).distinct().order_by(Racquet.brand).all())
    patterns = (lambda .0: [ r[0] for r in .0 ])(db.session.query(Racquet.string_pattern).distinct().filter(Racquet.string_pattern.isnot(None)).order_by(Racquet.string_pattern).all())
    return render_template('shop/racquets.html', racquet_list, brands, patterns, request.args, **('racquets', 'brands', 'patterns', 'filters'))

racquets = shop_bp.route('/racquets')(racquets)

def racquet_detail(racquet_id):
    racquet = Racquet.query.get_or_404(racquet_id)
    return render_template('shop/racquet_detail.html', racquet, **('racquet',))

racquet_detail = shop_bp.route('/racquets/<int:racquet_id>')(racquet_detail)

def scrape():
    import_enabled = current_app.config.get('SHOP_IMPORT_ENABLED', True)
    if import_enabled and request.method == 'POST':
        flash('Import désactivé par configuration (SHOP_IMPORT_ENABLED=0).', 'warning')
        return redirect(url_for('shop.scrape'))
# WARNING: Decompyle incomplete

scrape = shop_bp.route('/scrape', [
    'GET',
    'POST'], **('methods',))(scrape)

def delete_racquet(racquet_id):
    racquet = Racquet.query.get_or_404(racquet_id)
    db.session.delete(racquet)
    db.session.commit()
    flash(f'''Raquette {racquet} supprimée.''', 'success')
    return redirect(url_for('shop.racquets'))

delete_racquet = shop_bp.route('/racquets/<int:racquet_id>/delete', [
    'POST'], **('methods',))(delete_racquet)
