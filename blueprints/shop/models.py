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
            return f'{abs(self.balance):.1f} pts HL'
        if self.balance > 0:
            return f'{self.balance:.1f} pts HH'
        return '0 pts (Equilibrée)'
