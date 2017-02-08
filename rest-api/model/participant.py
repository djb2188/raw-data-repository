import clock

from model.base import Base
from sqlalchemy import Column, Integer, DateTime, BLOB, UniqueConstraint, ForeignKey, Index
from sqlalchemy.ext.declarative import declared_attr

class ParticipantBase(object):
  """Mixin with shared columns for Participant and ParticipantHistory"""

  # We tack 'P' on the front whenever we use this externally
  participantId = Column('participant_id', Integer, primary_key=True, autoincrement=False)

  # Incrementing version, starts at 1 and is incremented on each update.
  version = Column('version', Integer, nullable=False)

  # We tack 'B' on the front whenever we use this externally
  biobankId = Column('biobank_id', Integer, nullable=False)

  lastModified = Column('last_modified', DateTime, default=clock.CLOCK.now,
                        onupdate=clock.CLOCK.now, nullable=False)
  signUpTime = Column('sign_up_time', DateTime, default=clock.CLOCK.now, nullable=False)
  providerLink = Column('provider_link', BLOB)

  @declared_attr
  def hpoId(cls):
    return Column('hpo_id', Integer, ForeignKey('hpo.hpo_id'), nullable=False)

class Participant(ParticipantBase, Base):  
  __tablename__ = 'participant'  
  
Index('participant_biobank_id', Participant.biobankId, unique=True)  
Index('participant_hpo_id', Participant.hpoId)

class ParticipantHistory(ParticipantBase, Base):  
  __tablename__ = 'participant_history'
  version = Column('version', Integer, primary_key=True)

