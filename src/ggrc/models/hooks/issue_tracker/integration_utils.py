# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""This module contains common utils for integration functionality."""

from ggrc import db
from ggrc import settings
from ggrc.models import exceptions
from ggrc.models import all_models
from ggrc.integrations.constants import DEFAULT_ISSUETRACKER_VALUES as \
    default_values
from ggrc.integrations.synchronization_jobs.assessment_sync_job import \
    ASSESSMENT_STATUSES_MAPPING


def validate_issue_tracker_info(info):
  """Validates that component ID and hotlist ID are integers."""
  component_id = info.get('component_id')
  if component_id:
    try:
      int(component_id)
    except (TypeError, ValueError):
      raise exceptions.ValidationError('Component ID must be a number.')

  hotlist_id = info.get('hotlist_id')
  if hotlist_id:
    try:
      int(hotlist_id)
    except (TypeError, ValueError):
      raise exceptions.ValidationError('Hotlist ID must be a number.')


def is_already_linked(ticket_id):
  """Checks if ticket with ticket_id is already linked to GGRC object"""
  exists_query = db.session.query(
      all_models.IssuetrackerIssue.issue_id
  ).filter_by(issue_id=ticket_id).exists()
  return db.session.query(exists_query).scalar()


def normalize_issue_tracker_info(info):
  """Insures that component ID and hotlist ID are integers."""
  # TODO(anushovan): remove data type casting once integration service
  #   supports strings for following properties.
  component_id = info.get('component_id')
  if component_id:
    try:
      info['component_id'] = int(component_id)
    except (TypeError, ValueError):
      raise exceptions.ValidationError('Component ID must be a number.')

  hotlist_id = info.get('hotlist_id')
  if hotlist_id:
    try:
      info['hotlist_id'] = int(hotlist_id)
    except (TypeError, ValueError):
      raise exceptions.ValidationError('Hotlist ID must be a number.')


def set_values_for_missed_fields(assmt, issue_tracker_info):
  """Set values for empty issue tracked fields.

  Current list of fields with default values: component_id, hotlist_id,
    issue_type, priority, severity. They would be taken from default values if
    they are empty in appropriate audit.
  Current list of values that would be taken from assessment: title, status,
    due date.
  """
  audit_info = assmt.audit.issue_tracker or {}
  if not issue_tracker_info.get("component_id"):
    issue_tracker_info["component_id"] = audit_info.get("component_id") or\
        default_values["component_id"]

  if not issue_tracker_info.get("hotlist_id"):
    issue_tracker_info["hotlist_id"] = audit_info.get("hotlist_id") or\
        default_values["hotlist_id"]

  if not issue_tracker_info.get("issue_type"):
    issue_tracker_info["issue_type"] = audit_info.get("issue_type") or\
        default_values["issue_type"]

  if not issue_tracker_info.get("issue_priority"):
    issue_tracker_info["issue_priority"] = audit_info.get("issue_priority") or\
        default_values["issue_priority"]

  if not issue_tracker_info.get("issue_severity"):
    issue_tracker_info["issue_severity"] = audit_info.get("issue_severity") or\
        default_values["issue_severity"]

  if not issue_tracker_info.get("title"):
    issue_tracker_info["title"] = assmt.title

  if not issue_tracker_info.get("status"):
    issue_tracker_info["status"] = ASSESSMENT_STATUSES_MAPPING.get(
        assmt.status
    )

  if not issue_tracker_info.get('due_date'):
    issue_tracker_info['due_date'] = assmt.start_date


def build_issue_tracker_url(issue_id):
  """Build issue tracker URL by issue id."""
  issue_tracker_tmpl = settings.ISSUE_TRACKER_BUG_URL_TMPL
  url_tmpl = issue_tracker_tmpl if issue_tracker_tmpl else 'http://issue/%s'
  return url_tmpl % issue_id


def exclude_auditor_emails(emails):
  """Returns new email set with excluded auditor emails."""
  acl = all_models.AccessControlList
  acr = all_models.AccessControlRole

  if not isinstance(emails, set):
    emails = set(emails)

  auditor_emails = db.session.query(
      all_models.Person.email
  ).join(
      acl, acl.person_id == all_models.Person.id
  ).join(
      acr
  ).filter(
      acr.name == "Auditors",
      all_models.Person.email.in_(emails)
  ).distinct().all()

  emails_to_exlude = {line.email for line in auditor_emails}
  return emails - emails_to_exlude
