from extensions import db


class Racquet(db.Model):
    __tablename__ = 'racquet'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    head_size = db.Column(db.Float, nullable=True)
    length = db.Column(db.Float, nullable=True)
    strung_weight = db.Column(db.Float, nullable=True)
    unstrung_weight = db.Column(db.Float, nullable=True)
    balance = db.Column(db.Float, nullable=True)
    swingweight = db.Column(db.Integer, nullable=True)
    stiffness = db.Column(db.Integer, nullable=True)
    beam_width = db.Column(db.String(20), nullable=True)
    string_pattern = db.Column(db.String(10), nullable=True)
    string_tension = db.Column(db.String(20), nullable=True)
    price = db.Column(db.Float, nullable=True)
    url = db.Column(db.String(500), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    image_local = db.Column(db.String(200), nullable=True)
    player_type = db.Column(db.String(50), nullable=True)
    composition = db.Column(db.String(100), nullable=True)
    color = db.Column(db.String(50), nullable=True)
    is_current = db.Column(db.Boolean, default=False, nullable=False, server_default='0')
    release_year = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now())
    # ── Champs racqix ──────────────────────────────────────────────────────
    racqix_id = db.Column(db.String(50), nullable=True, unique=True, index=True)
    racqix_slug = db.Column(db.String(100), nullable=True)
    scores_power = db.Column(db.Integer, nullable=True)
    scores_control = db.Column(db.Integer, nullable=True)
    scores_spin = db.Column(db.Integer, nullable=True)
    category_tag = db.Column(db.String(30), nullable=True)
    player_level = db.Column(db.String(50), nullable=True)   # ex: "intermediate,pro"
    swing_style = db.Column(db.String(20), nullable=True)    # ex: "full"
    play_style = db.Column(db.String(50), nullable=True)     # ex: "baseliner"

    def __repr__(self):
        return f'{self.brand} {self.name}'

    @property
    def balance_label(self):
        if self.balance is None:
            return 'N/A'
        if self.balance < 0:
            return f'{abs(self.balance):.0f} pts HL'
        if self.balance > 0:
            return f'{self.balance:.0f} pts HH'
        return '0 pts (Équilibrée)'

    @property
    def balance_mm(self):
        """Distance en mm depuis la base du manche jusqu'au point d'équilibre.
        Une raquette standard mesure 27 pouces = 685.8 mm.
        balance en pts (1 pt = 1/8 inch = 3.175 mm).
        Point neutre = milieu = 685.8 / 2 = 342.9 mm.
        HL = tête légère → balance < milieu.
        """
        if self.balance is None:
            return None
        length_mm = (self.length or 27.0) * 25.4
        neutral_mm = length_mm / 2.0
        # balance négatif = HL, positif = HH
        return round(neutral_mm - self.balance * 3.175, 1)

    @property
    def head_size_cm2(self):
        """Taille du tamis en cm²  (1 sq.in = 6.4516 cm²)."""
        if self.head_size is None:
            return None
        return round(self.head_size * 6.4516, 0)

    @property
    def length_cm(self):
        """Longueur en cm (1 inch = 2.54 cm)."""
        if self.length is None:
            return None
        return round(self.length * 2.54, 2)

    @property
    def strung_weight_oz(self):
        """Poids cordé en oz (1 g = 0.035274 oz)."""
        if self.strung_weight is None:
            return None
        return round(self.strung_weight / 28.3495, 2)

    @property
    def unstrung_weight_oz(self):
        """Poids non-cordé en oz."""
        if self.unstrung_weight is None:
            return None
        return round(self.unstrung_weight / 28.3495, 2)


class RacqixString(db.Model):
    """Cordage issu de la base Racqix."""
    __tablename__ = 'racqix_string'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), nullable=False, unique=True, index=True)
    brand = db.Column(db.String(60), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    family = db.Column(db.String(30), nullable=True)
    shape = db.Column(db.String(20), nullable=True)
    string_type = db.Column(db.String(30), nullable=True, index=True)
    gauges_json = db.Column(db.Text, nullable=True)     # JSON list ex: ["1.25","1.30"]
    rating_comfort = db.Column(db.Integer, nullable=True)
    rating_control = db.Column(db.Integer, nullable=True)
    rating_power = db.Column(db.Integer, nullable=True)
    rating_spin = db.Column(db.Integer, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    @property
    def gauges(self):
        import json
        if not self.gauges_json:
            return []
        try:
            return json.loads(self.gauges_json)
        except Exception:
            return []

    @property
    def type_label(self):
        _map = {
            'co_polyester': 'Co-polyester',
            'polyester': 'Polyester',
            'multifilament': 'Multifilament',
            'natural_gut': 'Boyau naturel',
            'synthetic_gut': 'Synthétique',
            'hybrid': 'Hybride',
            'kevlar': 'Kevlar',
            'unknown': 'Autre',
        }
        return _map.get(self.string_type or '', self.string_type or 'Autre')

    @property
    def type_emoji(self):
        _map = {
            'co_polyester': '🔴',
            'polyester': '🔴',
            'multifilament': '🟢',
            'natural_gut': '🟡',
            'synthetic_gut': '⚪',
            'hybrid': '🔀',
            'kevlar': '⚫',
        }
        return _map.get(self.string_type or '', '⚪')

    def __repr__(self):
        return f'<RacqixString {self.brand} {self.name}>'
