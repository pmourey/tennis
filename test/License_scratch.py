class License(db.Model):
    __tablename__ = 'license'
    id = db.Column(db.Integer, primary_key=True)
    firstName = db.Column(db.String(20), nullable=False)
    lastName = db.Column(db.String(20), nullable=False)
    letter = db.Column(db.String(1), nullable=False)
    year = db.Column(db.Integer, nullable=False)  # Année de la licence
    gender = db.Column(db.Integer, nullable=False)  # Champ masculin/féminin (0 pour masculin, 1 pour féminin, 2 pour mixte)

    # # Define the relationship with Ranking using rankingId
    # rankingId = db.Column(db.Integer, db.ForeignKey('ranking.id'), nullable=False)
    # # ranking = relationship('Ranking', foreign_keys=[rankingId], backref=backref("ranking", uselist=False))
    # # ranking = relationship('Ranking', foreign_keys="[Ranking.rankingId]", backref=backref("ranking", uselist=False))
    # ranking = relationship('Ranking', foreign_keys="[Ranking.rankingId]")
    #
    # # Define the relationship with Ranking using bestRankingId
    # bestRankingId = db.Column(db.Integer, db.ForeignKey('ranking.id'), nullable=True)
    # #bestRanking = relationship('Ranking', foreign_keys=[bestRankingId], backref=backref("best_ranking", uselist=False))
    # # bestRanking = relationship('Ranking', foreign_keys="[Ranking.bestRankingId]", backref=backref("best_ranking", uselist=False))
    # bestRanking = relationship('Ranking', foreign_keys="[Ranking.bestRankingId]")

    # Define the relationship with Ranking using rankingId
    rankingId = db.Column(db.Integer, ForeignKey('ranking.id'), nullable=False)
    # ranking = relationship('Ranking', foreign_keys=[rankingId], back_populates='license')
    ranking = relationship('Ranking', foreign_keys="License.rankingId", back_populates='license', uselist=False, viewonly=True,
                             primaryjoin='License.rankingId == Ranking.id')

    # Define the relationship with Ranking using bestRankingId
    bestRankingId = db.Column(db.Integer, ForeignKey('ranking.id'), nullable=True)
    bestRanking = relationship('Ranking', foreign_keys='License.bestRankingId', back_populates='license', uselist=False, viewonly=True,
                              primaryjoin='License.bestRankingId == Ranking.id')
    # bestRanking = relationship('Ranking', foreign_keys=[bestRankingId])
    # # bestRanking = relationship('Ranking', foreign_keys=[bestRankingId], uselist=False,
    # #                            primaryjoin='License.bestRankingId == Ranking.id')
    # bestRanking = relationship('Ranking', foreign_keys=[bestRankingId], remote_side=[Ranking.id])

    # Define the back reference to rankings
    # rankings = relationship('Ranking', back_populates='license')
    rankings = relationship('Ranking', back_populates='license', foreign_keys=[rankingId])

    # Define the back reference to rankings with remote_side parameter
    # rankings = relationship('Ranking', back_populates='license', remote_side=[Ranking.licenseId])

    # Define the relationship with Player
    players = relationship('Player', back_populates='license')
