'''The definition of the questionnaire object and DB marshalling.
'''
import collections
import uuid

import fhir_datatypes

from data_access_object import DataAccessObject
from protorpc import message_types
from protorpc import messages


QUESTION_KEY_COLUMNS = ('questionnaire_id', 'parent_id')
QUESTION_COLUMNS = QUESTION_KEY_COLUMNS + (
    'linkId',
    'concept',
    'text',
    'type',
    'required',
    'repeats',
    'options',
    'option_col',
    'ordinal',
)

class Question(messages.Message):
  questionnaire_id = messages.StringField(1)
  question_id = messages.StringField(2)
  parent_id = messages.StringField(3)
  ordinal = messages.IntegerField(4)
  linkId = messages.StringField(5)
  concept = messages.MessageField(fhir_datatypes.Coding, 6, repeated=True)
  text = messages.StringField(7)
  type = messages.StringField(8)
  required = messages.BooleanField(9)
  repeats = messages.BooleanField(10)
  options = messages.MessageField(fhir_datatypes.Reference, 11, repeated=False)
  option = messages.MessageField(fhir_datatypes.Coding, 12, repeated=True)
  group = messages.MessageField('QuestionnaireGroup', 13, repeated=True)

class QuestionDao(DataAccessObject):
  def __init__(self):
    # Option is a keyword in MySQL, we have to map it to option_col.
    super(QuestionDao, self).__init__(resource=Question,
                                      table='question',
                                      columns=QUESTION_COLUMNS,
                                      key_columns=QUESTION_KEY_COLUMNS,
                                      column_map={'option_col': 'option'})
    self.set_synthetic_fields(QUESTION_KEY_COLUMNS + ('ordinal',))

  def link(self, obj, parent, ordinal):
    parent_type = type(parent)
    if parent_type == QuestionnaireGroup:
      obj.parent_id = parent.questionnaire_group_id
      obj.questionnaire_id = parent.questionnaire_id
    elif parent_type == Question:
      obj.parent_id = parent.question_id
      obj.questionnaire_id = parent.questionnaire_id
    else: # Either Questionnaire or the ResourceContainer.
      obj.parent_id = parent.id
      obj.questionnaire_id = parent.id

    if not obj.question_id:
      obj.question_id = str(uuid.uuid4())

    obj.ordinal = ordinal


QUESTIONNAIRE_GROUP_KEY_COLUMNS = (
    'questionnaire_id',
    'questionnaire_group_id',
    'parent_id')

QUESTIONNAIRE_GROUP_COLUMNS = QUESTIONNAIRE_GROUP_KEY_COLUMNS + (
    'linkId',
    'concept',
    'text',
    'type',
    'required',
    'repeats',
    'ordinal',
)

class QuestionnaireGroup(messages.Message):
  """A group of questions in a questionnaire."""
  questionnaire_id = messages.StringField(1)
  questionnaire_group_id = messages.StringField(2)
  # Can be a child of either a question group or a Questionnaire.
  parent_id = messages.StringField(3)
  ordinal = messages.IntegerField(4)
  linkId = messages.StringField(5)
  concept = messages.MessageField(fhir_datatypes.Coding, 6, repeated=True)
  text = messages.StringField(7)
  type = messages.StringField(8)
  required = messages.BooleanField(9)
  repeats = messages.BooleanField(10)
  group = messages.MessageField('QuestionnaireGroup', 11, repeated=True)
  question = messages.MessageField(Question, 12, repeated=True)

class QuestionnaireGroupDao(DataAccessObject):
  def __init__(self):
    super(QuestionnaireGroupDao, self).__init__(
        resource=QuestionnaireGroup,
        table='questionnaire_group',
        columns=QUESTIONNAIRE_GROUP_COLUMNS,
        key_columns=QUESTIONNAIRE_GROUP_KEY_COLUMNS)
    self.set_synthetic_fields(QUESTIONNAIRE_GROUP_KEY_COLUMNS + ('ordinal',))

  def link(self, obj, parent, ordinal):
    parent_type = type(parent)
    if parent_type == QuestionnaireGroup:
      obj.parent_id = parent.questionnaire_group_id
      obj.questionnaire_id = parent.questionnaire_id
    elif parent_type == Question:
      obj.parent_id = parent.question_id
      obj.questionnaire_id = parent.questionnaire_id
    else: # Either Questionnaire or the ResourceContainer.
      obj.parent_id = parent.id
      obj.questionnaire_id = parent.id

    obj.ordinal = ordinal
    if not obj.questionnaire_group_id:
      obj.questionnaire_group_id = str(uuid.uuid4())



QUESTIONNAIRE_KEY_COLUMNS = ('id',)
QUESTIONNAIRE_COLUMNS = QUESTIONNAIRE_KEY_COLUMNS + (
    'resourceType',
    'identifier',
    'version',
    'status',
    'date',
    'publisher',
    'telecom',
    'text',
    'contained',
)


class Questionnaire(messages.Message):
  """The questionnaire resource definition"""
  resourceType = messages.StringField(1)
  id = messages.StringField(2)
  identifier = messages.MessageField(fhir_datatypes.Identifier, 3,
                                     repeated=True)
  version = messages.StringField(4)
  status = messages.StringField(5)
  date = messages.StringField(6)
  publisher = messages.StringField(7)
  telecom = messages.MessageField(fhir_datatypes.ContactPoint, 8, repeated=True)
  subjectType = messages.StringField(9)
  group = messages.MessageField(QuestionnaireGroup, 10, repeated=False)
  text = messages.MessageField(fhir_datatypes.Narrative, 11, repeated=True)
  contained = messages.MessageField(fhir_datatypes.DomainUsageResource,
                                    12, repeated=True)

class QuestionnaireCollection(messages.Message):
  """Collection of Questionnaires."""
  items = messages.MessageField(Questionnaire, 1, repeated=True)


class QuestionnaireDao(DataAccessObject):
  def __init__(self):
    super(QuestionnaireDao, self).__init__(
        resource=Questionnaire,
        table='questionnaire',
        columns=QUESTIONNAIRE_COLUMNS,
        key_columns=QUESTIONNAIRE_KEY_COLUMNS)
  def assemble(self, questionnaire):
    # Request_obj here should have the questionnaire id set in the field 'id'.
    questions = QUESTION_DAO.list(Question(questionnaire_id=questionnaire.id))
    questionnaire_groups = QUESTIONNAIRE_GROUP_DAO.list(
        QuestionnaireGroup(questionnaire_id=questionnaire.id))

    parent_to_questions = collections.defaultdict(list)
    parent_to_groups = collections.defaultdict(list)

    for question in questions:
      parent_to_questions[question.parent_id].append(question)

    for group in questionnaire_groups:
      parent_to_groups[group.parent_id].append(group)

    # Questionnaires have a single group.
    groups = parent_to_groups[questionnaire.id]
    if len(groups) > 1:
      raise BaseException("Found questionnaire with multiple groups")
    if groups:
      questionnaire.group = groups[0]

    # QuestionnaireGroups may contain multiple QuestionnaireGroups and multiple
    # questions.
    for group in questionnaire_groups:
      group.group = sorted(parent_to_groups[group.questionnaire_group_id],
                           key=lambda g: g.ordinal)

      group.question = sorted(parent_to_questions[group.questionnaire_group_id],
                              key=lambda q: q.ordinal)

    # Questions may contain multiple QuestionnaireGroups.
    for question in questions:
      question.group = sorted(parent_to_groups[question.question_id],
                              key=lambda g: g.ordinal)

QUESTION_DAO = QuestionDao()
QUESTIONNAIRE_GROUP_DAO = QuestionnaireGroupDao()


QUESTION_DAO.add_child_message('group', QUESTIONNAIRE_GROUP_DAO)

QUESTIONNAIRE_GROUP_DAO.add_child_message('group', QUESTIONNAIRE_GROUP_DAO)
QUESTIONNAIRE_GROUP_DAO.add_child_message('question', QUESTION_DAO)

DAO = QuestionnaireDao()
DAO.add_child_message('group', QUESTIONNAIRE_GROUP_DAO)