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
    created_at = db.Column(db.DateTime, default=db.func.now())

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
