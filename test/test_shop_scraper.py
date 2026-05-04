import types

from bs4 import BeautifulSoup

from blueprints.shop import scraper


def _product_html(name='Hyper ProStaff 7.1 Zone', manufacturer='Wilson', pcode='H71'):
    return f'''
    <div class="product">
      <div class="rac_name">{name}</div>
      <img class="rac_img" src="http://example.com/{pcode}.jpg" />
      <table>
        <tr><th>Manufacturer</th><td>{manufacturer}</td></tr>
        <tr><th>Head Size</th><td>95 sq. in.</td></tr>
        <tr><th>String Pattern</th><td>16 Mains/19 Crosses</td></tr>
      </table>
      <a href="/compare?x=1&pcode={pcode}">TW</a>
    </div>
    '''


def test_parse_product_uses_manufacturer_for_brand():
    soup = BeautifulSoup(_product_html(), 'lxml')
    data = scraper.parse_product(soup.select_one('div.product'))

    assert data['brand'] == 'Wilson'
    assert data['name'] == 'Hyper ProStaff 7.1 Zone'
    assert data['pcode'] == 'H71'
    assert data['head_size'] == 95.0
    assert data['string_pattern'] == '16x19'


def test_extract_brand_and_name_no_fake_brand_when_unknown():
    brand, name = scraper.extract_brand_and_name('Hyper ProStaff 7.1 Zone')
    assert brand == 'Unknown'
    assert name == 'Hyper ProStaff 7.1 Zone'


def test_fetch_manufacturers_returns_value_label(monkeypatch):
    html = '''
    <select id="manufacturer">
      <option value="">Select</option>
      <option value="Wilson">Wilson</option>
      <option value="HEAD">Head</option>
    </select>
    '''

    def fake_get(*args, **kwargs):
        return types.SimpleNamespace(text=html)

    monkeypatch.setattr(scraper.requests, 'get', fake_get)
    manufacturers = scraper.fetch_manufacturers()

    assert manufacturers == [
        {'value': 'Wilson', 'label': 'Wilson'},
        {'value': 'HEAD', 'label': 'Head'},
    ]


def test_scrape_racquet_by_pcode(monkeypatch):
    html = '''
    <h2>Wilson Hyper ProStaff 7.1 Zone</h2>
    <div class="with_image cf">
      <img class="racimage" src="http://img.tennis-warehouse.com/new_thumb/H71-thumb.jpg" />
      <table>
        <tr><th>Head Size:</th><td>95 sq. in. / 613 sq. cm.</td></tr>
        <tr><th>Length:</th><td>27.00 inches / 68.58 cm</td></tr>
        <tr><th>String Pattern:</th><td>16 Mains / 19 Crosses</td></tr>
      </table>
    </div>
    '''

    def fake_get(*args, **kwargs):
        return types.SimpleNamespace(status_code=200, text=html)

    monkeypatch.setattr(scraper.requests, 'get', fake_get)
    data = scraper.scrape_racquet_by_pcode('h71')

    assert data['pcode'] == 'H71'
    assert data['brand'] == 'Wilson'
    assert data['name'] == 'Hyper ProStaff 7.1 Zone'
    assert data['head_size'] == 95.0
    assert data['length'] == 27.0
    assert data['string_pattern'] == '16x19'


def test_parse_weight_ounces_to_grams():
    # 11.5 oz ~= 326.0 g
    assert scraper._parse_weight_oz_to_g('11.5 oz / 326 g') == 326.0


def test_parse_weight_grams_when_no_oz():
    assert scraper._parse_weight_oz_to_g('300 g') == 300.0


def test_build_params_with_stiffness_range():
    params = scraper._build_params(manufacturer='Wilson', current_only=False, stiffness_min=20, stiffness_max=29)
    assert params['manufacturer'] == 'Wilson'
    assert params['fMin'] == '20'
    assert params['fMax'] == '29'


def test_build_params_current_only_uses_fixed_checkbox_value():
    params = scraper._build_params(manufacturer='Wilson', current_only=True)
    assert params['current'] == 'Y'
    assert params['currentcheckbox'] == 'ASICS'


def test_stiffness_ranges_cover_0_to_90():
    assert scraper._stiffness_ranges() == [
        (0, 9),
        (10, 19),
        (20, 29),
        (30, 39),
        (40, 49),
        (50, 59),
        (60, 69),
        (70, 79),
        (80, 90),
    ]


def test_collect_products_by_stiffness_deduplicates(monkeypatch):
    html = '<div class="product"><div class="rac_name">Wilson X</div></div>'
    soup = BeautifulSoup(html, 'lxml')
    product = soup.select_one('div.product')

    def fake_partitioned(**kwargs):
        # Return same block for every bucket to verify dedup.
        return [product]

    def fake_fetch_products(params):
        # Non-filtered fallback also returns the same block.
        return [product]

    monkeypatch.setattr(scraper, '_collect_products_partitioned', fake_partitioned)
    monkeypatch.setattr(scraper, '_fetch_products', fake_fetch_products)

    products = scraper._collect_products_by_stiffness(manufacturer='Wilson', current_only=False)
    assert len(products) == 1

