# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Integration tests for assessments with IssueTracker integration."""
# pylint: disable=too-many-lines
# this module will be refactored in the future when we make base testcase class
# for issuetracker integration.

from collections import OrderedDict

import mock
import ddt

import sqlalchemy as sa

from ggrc import db
from ggrc import models
from ggrc import settings
from ggrc.app import app
from ggrc.models import all_models
from ggrc.models.hooks.issue_tracker import assessment_integration
from ggrc.models.hooks.issue_tracker import integration_utils
from ggrc.models.hooks.issue_tracker import issue_tracker_params_builder \
    as params_builder
from ggrc.integrations.synchronization_jobs import sync_utils
from ggrc.integrations.constants import DEFAULT_ISSUETRACKER_VALUES
from ggrc.integrations.synchronization_jobs.assessment_sync_job import \
    ASSESSMENT_STATUSES_MAPPING
from ggrc.integrations import synchronization_jobs
from ggrc.access_control.role import AccessControlRole

from integration.ggrc.models import factories
from integration.ggrc import generator
from integration.ggrc.access_control import acl_helper
from integration.ggrc.snapshotter import SnapshotterBaseTestCase

TICKET_ID = 123


# pylint: disable=too-many-public-methods
@ddt.ddt
class TestIssueTrackerIntegration(SnapshotterBaseTestCase):
  """Test set for IssueTracker integration functionality."""

  # pylint: disable=invalid-name

  def setUp(self):
    # pylint: disable=super-on-old-class
    # pylint seems to get confused, mro chain successfully resolves and returns
    # <type 'object'> as last entry.
    super(TestIssueTrackerIntegration, self).setUp()

    self.client.get('/login')

  DEFAULT_ASSESSMENT_ATTRS = {
      "title": "title1",
      "context": None,
      "status": "Draft",
      "enabled": True,
      "component_id": 1234,
      "hotlist_id": 4321,
      "issue_id": 654321,
      "issue_type": "PROCESS",
      "issue_priority": "P2",
      "issue_severity": "S1",
  }

  DEFAULT_TICKET_ATTRS = {
      "component_id": 1234,
      "hotlist_id": 4321,
      "issue_id": 654321,
      "status": "new",
      "issue_type": "Default Issue type",
      "issue_priority": "P1",
      "issue_severity": "S2",
      "title": "test title",
      "verifier": "user@example.com",
      "assignee": "user@example.com",
      "ccs": ["user@example.com"],
  }

  def request_payload_builder(self, issue_attrs, audit):
    """Build payload for update request to Issue Tracker"""
    payload_attrs = dict(self.DEFAULT_ASSESSMENT_ATTRS, **issue_attrs)
    payload = {"assessment": {
        "title": payload_attrs["title"],
        "context": None,
        "audit": {
            "id": audit.id,
            "type": audit.type,
        },
        "status": "Completed",
        "issue_tracker": {
            "enabled": payload_attrs["enabled"],
            "component_id": payload_attrs["component_id"],
            "hotlist_id": payload_attrs["hotlist_id"],
            "issue_id": payload_attrs["issue_id"],
            "issue_type": payload_attrs["issue_type"],
            "issue_priority": payload_attrs["issue_priority"],
            "issue_severity": payload_attrs["issue_severity"],
            "title": payload_attrs["title"],
        }
    }}
    return payload

  def response_payload_builder(self, ticket_attrs):
    """Build payload for response from Issue Tracker via get_issue method"""
    payload_attrs = dict(self.DEFAULT_TICKET_ATTRS, **ticket_attrs)
    payload = {"issueState": {
        "component_id": payload_attrs["component_id"],
        "hotlist_id": payload_attrs["hotlist_id"],
        "issue_id": payload_attrs["issue_id"],
        "status": payload_attrs["status"],
        "issue_type": payload_attrs["issue_type"],
        "issue_priority": payload_attrs["issue_priority"],
        "issue_severity": payload_attrs["issue_severity"],
        "title": payload_attrs["title"],
        "verifier": payload_attrs["verifier"],
        "assignee": payload_attrs["assignee"],
        "ccs": payload_attrs["ccs"],
    }}
    return payload

  def put_request_payload_builder(self, issue_attrs):
    """Build payload for PUT request to Issue Tracker"""
    payload_attrs = dict(self.DEFAULT_ASSESSMENT_ATTRS, **issue_attrs)
    payload = {
        "issue_tracker": {
            "enabled": payload_attrs["enabled"],
            "status": payload_attrs["status"],
            "component_id": payload_attrs["component_id"],
            "hotlist_id": payload_attrs["hotlist_id"],
            "issue_id": payload_attrs["issue_id"],
            "issue_type": payload_attrs["issue_type"],
            "issue_priority": payload_attrs["issue_priority"],
            "issue_severity": payload_attrs["issue_severity"],
            "title": payload_attrs["title"],
        }
    }
    return payload

  def check_issuetracker_issue_fields(self,
                                      issue_tracker_issue,
                                      assmt_attrs):
    """Checks issuetracker_issue were updated correctly.

    Make assertions to check if issue tracker fields were updated according
    our business logic.
    For Assessment model we should get all attributes from linked assessment.
    """
    self.assertTrue(issue_tracker_issue.enabled)
    # According to our business logic all attributes should be taken
    # from assessment attributes
    self.assertEqual(
        issue_tracker_issue.title,
        assmt_attrs["assessment"]["title"]
    )
    self.assertEqual(
        int(issue_tracker_issue.component_id),
        assmt_attrs["assessment"]["issue_tracker"]["component_id"]
    )
    self.assertEqual(
        int(issue_tracker_issue.hotlist_id),
        assmt_attrs["assessment"]["issue_tracker"]["hotlist_id"]
    )
    self.assertEqual(
        issue_tracker_issue.issue_priority,
        assmt_attrs["assessment"]["issue_tracker"]["issue_priority"]
    )
    self.assertEqual(
        issue_tracker_issue.issue_severity,
        assmt_attrs["assessment"]["issue_tracker"]["issue_severity"]
    )
    self.assertEqual(
        int(issue_tracker_issue.issue_id),
        assmt_attrs["assessment"]["issue_tracker"]["issue_id"]
    )
    self.assertEqual(
        issue_tracker_issue.issue_type,
        assmt_attrs["assessment"]["issue_tracker"]["issue_type"]
    )

  @ddt.data(
      ({"title": "first_title"}, {"title": "other_title"}),
      ({"issue_type": "type1"}, {"issue_type": "process"}),
      ({"issue_severity": "S0"}, {"issue_severity": "S1"}),
      ({"issue_priority": "P0"}, {"issue_priority": "P1"}),
      ({"hotlist_id": 1234}, {"hotlist_id": 4321}),
      ({"component_id": 1234}, {"component_id": 4321}),
      ({"status": "Draft"}, {"status": "fixed"}),
  )
  @ddt.unpack
  @mock.patch("ggrc.integrations.issues.Client.update_issue")
  @mock.patch.object(settings, "ISSUE_TRACKER_ENABLED", True)
  def test_new_linked_assessment(self, assmt_attrs, ticket_attrs, upd_mock):
    """Test link new Assessment to IssueTracker ticket sets correct fields"""
    with factories.single_commit():
      audit = factories.AuditFactory()
      factories.IssueTrackerIssueFactory(
          enabled=True,
          issue_tracked_obj=audit
      )

    assmt_request_payload = self.request_payload_builder(assmt_attrs, audit)
    response_payload = self.response_payload_builder(ticket_attrs)

    with mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                           return_value=True):
      with mock.patch("ggrc.integrations.issues.Client.get_issue",
                      return_value=response_payload) as get_mock:
        response = self.api.post(all_models.Assessment, assmt_request_payload)

    get_mock.assert_called_once()
    upd_mock.assert_called_once()
    self.assertEqual(response.status_code, 201)
    assmt_id = response.json.get("assessment").get("id")
    it_issue = models.IssuetrackerIssue.get_issue("Assessment", assmt_id)
    self.check_issuetracker_issue_fields(it_issue, assmt_request_payload)

  def test_fill_missing_values_from_audit(self):
    """Check prepare_json_method get missed values from audit."""
    with factories.single_commit():
      audit = factories.AuditFactory()
      factories.IssueTrackerIssueFactory(
          enabled=True,
          issue_tracked_obj=audit,
          component_id=213,
          hotlist_id=333,
          issue_type="BUG",
          issue_priority="S0",
          issue_severity="P0",
      )
      assmt = factories.AssessmentFactory(
          audit=audit,
      )
      factories.IssueTrackerIssueFactory(
          enabled=True,
          issue_tracked_obj=assmt
      )

    audit_issue_tracker_info = audit.issuetracker_issue.to_dict()
    assmt_issue_tracker_info = assmt.issuetracker_issue.to_dict()

    integration_utils.set_values_for_missed_fields(assmt,
                                                   assmt_issue_tracker_info)

    fields_to_check = ["component_id", "hotlist_id", "issue_type",
                       "issue_priority", "issue_severity"]
    for field in fields_to_check:
      self.assertEqual(assmt_issue_tracker_info[field],
                       audit_issue_tracker_info[field])

  def test_fill_missing_values_from_default(self):
    """Check prepare_json_method get missed values from default values."""
    with factories.single_commit():
      assmt = factories.AssessmentFactory()
      factories.IssueTrackerIssueFactory(
          enabled=True,
          issue_tracked_obj=assmt
      )

    assmt_issue_tracker_info = assmt.issuetracker_issue.to_dict()

    integration_utils.set_values_for_missed_fields(assmt,
                                                   assmt_issue_tracker_info)

    fields_to_check = ["component_id", "hotlist_id", "issue_type",
                       "issue_priority", "issue_severity"]
    for field in fields_to_check:
      self.assertEqual(assmt_issue_tracker_info[field],
                       DEFAULT_ISSUETRACKER_VALUES[field])

  def test_fill_missing_values_from_assmt(self):
    """Check prepare_json_method get missed values from default values."""
    with factories.single_commit():
      assmt = factories.AssessmentFactory(
          start_date="2015-10-09",
          status="Not Started",
          title="title",
      )
      factories.IssueTrackerIssueFactory(
          enabled=True,
          issue_tracked_obj=assmt
      )

    assmt_issue_tracker_info = assmt.issuetracker_issue.to_dict()

    integration_utils.set_values_for_missed_fields(assmt,
                                                   assmt_issue_tracker_info)

    self.assertEqual(assmt_issue_tracker_info["title"],
                     assmt.title)
    self.assertEqual(assmt_issue_tracker_info["due_date"],
                     assmt.start_date)
    self.assertEqual(assmt_issue_tracker_info["status"],
                     ASSESSMENT_STATUSES_MAPPING[assmt.status])

  @mock.patch("ggrc.integrations.issues.Client.update_issue")
  @mock.patch.object(settings, "ISSUE_TRACKER_ENABLED", True)
  def test_existing_assmt_link(self, update_mock):
    """Test Assessment link to another ticket """
    with factories.single_commit():
      audit = factories.AuditFactory()
      factories.IssueTrackerIssueFactory(
          enabled=True,
          issue_tracked_obj=audit
      )
      iti = factories.IssueTrackerIssueFactory(
          enabled=True,
          issue_id=TICKET_ID,
          issue_tracked_obj=factories.AssessmentFactory(audit=audit)
      )

    new_ticket_id = TICKET_ID + 1
    new_data = {"issue_id": new_ticket_id}
    issue_request_payload = self.put_request_payload_builder(new_data)
    response_payload = self.response_payload_builder(new_data)
    with mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                           return_value=True):
      with mock.patch("ggrc.integrations.issues.Client.get_issue",
                      return_value=response_payload) as get_mock:
        response = self.api.put(iti.issue_tracked_obj, issue_request_payload)
    get_mock.assert_called_once()
    self.assert200(response)

    # check if data was changed in our DB
    issue_id = response.json.get("assessment").get("id")
    issue_tracker_issue = models.IssuetrackerIssue.get_issue(
        "Assessment",
        issue_id,
    )
    self.assertEqual(int(issue_tracker_issue.issue_id), new_ticket_id)

    # check detach comment was sent
    detach_comment_tmpl = params_builder.AssessmentParamsBuilder.DETACH_TMPL
    comment = detach_comment_tmpl.format(new_ticket_id=new_ticket_id)
    expected_args = (TICKET_ID, {"comment": comment})
    self.assertEqual(expected_args, update_mock.call_args[0])

  @mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                     return_value=True)
  @mock.patch.object(settings, "ISSUE_TRACKER_ENABLED", True)
  def test_already_linked_ticket(self, enabled_mock):
    """Test Assessment w/o IT couldn't be linked to already linked ticket"""
    with factories.single_commit():
      audit = factories.AuditFactory()
      factories.IssueTrackerIssueFactory(
          enabled=True,
          issue_tracked_obj=audit
      )
      factories.IssueTrackerIssueFactory(
          enabled=True,
          issue_id=TICKET_ID,
          issue_tracked_obj=factories.AssessmentFactory(audit=audit)
      )
      new_assmt = factories.AssessmentFactory()

    issue_data = {"issue_id": TICKET_ID}
    issue_request_payload = self.put_request_payload_builder(issue_data)
    response = self.api.put(new_assmt, issue_request_payload)
    self.assert200(response)
    self.assertTrue(response.json["assessment"]["issue_tracker"]["_warnings"])
    issue_id = response.json.get("assessment").get("id")
    issue_tracker_issue = models.IssuetrackerIssue.get_issue(
        "Assessment",
        issue_id,
    )
    self.assertFalse(issue_tracker_issue)
    enabled_mock.assert_called()

  @mock.patch("ggrc.integrations.issues.Client.update_issue")
  @mock.patch.object(settings, "ISSUE_TRACKER_ENABLED", True)
  def test_creating_new_ticket_for_linked_issue(self, update_mock):
    """Test create new ticket for already linked assessment"""
    with factories.single_commit():
      audit = factories.AuditFactory()
      factories.IssueTrackerIssueFactory(
          enabled=True,
          issue_tracked_obj=audit
      )
      iti = factories.IssueTrackerIssueFactory(
          enabled=True,
          issue_id=TICKET_ID,
          issue_tracked_obj=factories.AssessmentFactory(audit=audit)
      )
    new_data = {"issue_id": ''}
    issue_request_payload = self.put_request_payload_builder(new_data)
    with mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                           return_value=True):
      with mock.patch("ggrc.integrations.issues.Client.create_issue",
                      return_value={"issueId": TICKET_ID + 1}) as create_mock:
        response = self.api.put(iti.issue_tracked_obj, issue_request_payload)
    self.assert200(response)

    # Detach comment should be sent to previous ticket
    update_mock.assert_called_once()
    self.assertEqual(TICKET_ID, update_mock.call_args[0][0])
    create_mock.assert_called_once()

    # check if data was changed in our DB
    issue_id = response.json.get("assessment").get("id")
    issue_tracker_issue = models.IssuetrackerIssue.get_issue(
        "Assessment",
        issue_id,
    )
    self.assertNotEqual(int(issue_tracker_issue.issue_id), TICKET_ID)

  @mock.patch('ggrc.integrations.issues.Client.create_issue')
  @mock.patch.object(settings, "ISSUE_TRACKER_ENABLED", True)
  def test_complete_assessment_create_issue(self, mock_create_issue):
    """Test the creation of issue for completed assessment."""
    audit = factories.AuditFactory()

    self.api.post(all_models.Assessment, {
        'assessment': {
            'title': 'Assessment1',
            'context': None,
            'audit': {
                'id': audit.id,
                'type': audit.type,
            },
            'status': 'Completed',
        }
    })
    asmt = all_models.Assessment.query.filter_by(title='Assessment1').one()

    with mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                           return_value=True):
      issue_params = {
          'enabled': True,
          'component_id': hash('Default Component id'),
          'hotlist_id': hash('Default Hotlist id'),
          'issue_type': 'Default Issue type',
          'issue_priority': 'Default Issue priority',
          'issue_severity': 'Default Issue severity',
      }
      self.api.put(asmt, {'issue_tracker': issue_params})
      mock_create_issue.assert_called_once()
      # pylint: disable=W0212
      self.assertEqual(mock_create_issue._mock_call_args[0][0]['status'],
                       'VERIFIED')

  @mock.patch.object(settings, "ISSUE_TRACKER_ENABLED", True)
  def test_update_issuetracker_info(self):
    """Test that Issue Tracker issues are updated by the utility."""
    cli_patch = mock.patch.object(sync_utils.issues, 'Client')
    hook_patch = mock.patch.object(assessment_integration,
                                   '_is_issue_tracker_enabled',
                                   return_value=True)
    with cli_patch, hook_patch:
      iti_issue_id = []
      for _ in xrange(2):
        iti = factories.IssueTrackerIssueFactory()
        iti_issue_id.append(iti.issue_id)
        asmt = iti.issue_tracked_obj
        asmt_id = asmt.id
        audit = asmt.audit
        self.api.modify_object(audit, {
            'issue_tracker': {
                'enabled': True,
                'component_id': '11111',
                'hotlist_id': '222222',
            },
        })
        asmt = db.session.query(models.Assessment).get(asmt_id)
        self.api.modify_object(asmt, {
            'issue_tracker': {
                'enabled': True,
                'component_id': '11111',
                'hotlist_id': '222222',
            },
        })
        asmt = db.session.query(models.Assessment).get(asmt_id)
        self.api.modify_object(asmt, {
            'issue_tracker': {
                'enabled': True,
                'component_id': '11111',
                'hotlist_id': '222222',
                'issue_priority': 'P4',
                'issue_severity': 'S3',
            },
        })
      self.api.delete(asmt)

    cli_mock = mock.MagicMock()
    cli_mock.update_issue.return_value = None
    cli_mock.search.return_value = {
        'issues': [
            {
                'issueId': iti_issue_id[0],
                'issueState': {
                    'status': 'FIXED', 'type': 'bug2',
                    'priority': 'P2', 'severity': 'S2',
                },
            },
        ],
        'next_page_token': None,
    }

    with mock.patch.object(sync_utils.issues, 'Client', return_value=cli_mock):
      synchronization_jobs.sync_assessment_attributes()
      cli_mock.update_issue.assert_called_once_with(
          iti_issue_id[0], {
              'status': 'ASSIGNED',
              'priority': u'P4',
              'type': None,
              'severity': u'S3',
              'ccs': [],
              'component_id': 11111
          })

  # pylint: disable=unused-argument
  @mock.patch('ggrc.integrations.issues.Client.update_issue')
  @mock.patch.object(settings, "ISSUE_TRACKER_ENABLED", True)
  def test_update_issuetracker_assignee(self, mocked_update_issue):
    """Test assignee sync in case it has been updated."""
    email1 = "email1@example.com"
    email2 = "email2@example.com"
    assignee_role_id = AccessControlRole.query.filter_by(
        object_type="Assessment",
        name="Assignees"
    ).first().id
    assignees = [factories.PersonFactory(email=email2),
                 factories.PersonFactory(email=email1)]
    iti_issue_id = []
    iti = factories.IssueTrackerIssueFactory(enabled=True)
    iti_issue_id.append(iti.issue_id)
    asmt = iti.issue_tracked_obj
    asmt_title = asmt.title
    with mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                           return_value=True):
      acl = [acl_helper.get_acl_json(assignee_role_id, assignee.id)
             for assignee in assignees]
      self.api.put(asmt, {
          "access_control_list": acl
      })
      kwargs = {'status': 'ASSIGNED',
                'component_id': None,
                'severity': None,
                'title': asmt_title,
                'hotlist_ids': [],
                'priority': None,
                'assignee': email1,
                'verifier': email1}
      mocked_update_issue.assert_called_once_with(iti_issue_id[0], kwargs)

  @mock.patch('ggrc.integrations.issues.Client.update_issue')
  @mock.patch.object(settings, "ISSUE_TRACKER_ENABLED", True)
  def test_update_issuetracker_title(self, mocked_update_issue):
    """Test title sync in case it has been updated."""
    with mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                           return_value=True):
      iti_issue_id = []
      iti = factories.IssueTrackerIssueFactory(enabled=True)
      iti_issue_id.append(iti.issue_id)
      asmt = iti.issue_tracked_obj
      new_title = "New Title"
      self.api.put(asmt, {"title": new_title})
      kwargs = {'status': 'ASSIGNED',
                'component_id': None,
                'severity': None,
                'title': new_title,
                'hotlist_ids': [],
                'priority': None}
      mocked_update_issue.assert_called_once_with(iti_issue_id[0], kwargs)

      issue = db.session.query(models.IssuetrackerIssue).get(iti.id)
      self.assertEqual(issue.title, new_title)

  @mock.patch('ggrc.integrations.issues.Client.update_issue')
  @mock.patch.object(settings, "ISSUE_TRACKER_ENABLED", True)
  def test_update_issuetracker_due_date(self, mocked_update_issue):
    """Test title sync in case it has been updated."""
    with mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                           return_value=True):
      iti_issue_id = []
      iti = factories.IssueTrackerIssueFactory(enabled=True)
      iti_issue_id.append(iti.issue_id)
      asmt = iti.issue_tracked_obj
      new_due_date = '2018-09-25'
      custom_fields = [{
          'name': 'Due Date',
          'value': new_due_date,
          'type': 'DATE',
          'display_string': 'Due Date',
      }]
      self.api.put(asmt, {
          'start_date': new_due_date,
          'title': 'title'
      })
      kwargs = {'status': 'ASSIGNED',
                'component_id': None,
                'severity': None,
                'title': 'title',
                'hotlist_ids': [],
                'priority': None,
                'custom_fields': custom_fields}
      mocked_update_issue.assert_called_once_with(iti_issue_id[0], kwargs)

      issue = db.session.query(models.IssuetrackerIssue).get(iti.id)
      self.assertEqual(issue.due_date.strftime("%Y-%m-%d"), new_due_date)

  # pylint: disable=protected-access
  # pylint: disable=too-many-locals
  @ddt.data(
      ('Not Started', {'status': 'ASSIGNED'}),
      ('In Progress', {'status': 'ASSIGNED'}),
      ('In Review', {'status': 'FIXED'}),
      ('Rework Needed', {'status': 'ASSIGNED'}),
      ('Completed', {
          'status': 'VERIFIED',
          'comment': assessment_integration._STATUS_CHANGE_COMMENT_TMPL
      }),
      ('Deprecated', {
          'status': 'OBSOLETE',
          'comment': assessment_integration._STATUS_CHANGE_COMMENT_TMPL
      }),
  )
  @ddt.unpack
  @mock.patch('ggrc.integrations.issues.Client.update_issue')
  @mock.patch.object(settings, "ISSUE_TRACKER_ENABLED", True)
  def test_change_assessment_status(self, status,
                                    additional_kwargs,
                                    mocked_update_issue):
    """Issue status should be changed for assessment
    with {status} status."""
    email1 = "email1@example.com"
    assignee_role_id = AccessControlRole.query.filter_by(
        object_type="Assessment",
        name="Assignees"
    ).first().id
    assignees = [factories.PersonFactory(email=email1)]
    iti_issue_id = []
    iti = factories.IssueTrackerIssueFactory(enabled=True)
    iti_issue_id.append(iti.issue_id)
    asmt = iti.issue_tracked_obj
    asmt_title = asmt.title
    with mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                           return_value=True):
      acl = [acl_helper.get_acl_json(assignee_role_id, assignee.id)
             for assignee in assignees]
      self.api.put(asmt, {
          "access_control_list": acl,
          "status": status,
      })
      kwargs = {'component_id': None,
                'severity': None,
                'title': asmt_title,
                'hotlist_ids': [],
                'priority': None,
                'assignee': email1,
                'verifier': email1}
      asmt_link = assessment_integration._get_assessment_url(asmt)
      if 'comment' in additional_kwargs:
        additional_kwargs['comment'] = \
            additional_kwargs['comment'] % (status, asmt_link)
      kwargs.update(additional_kwargs)
      mocked_update_issue.assert_called_once_with(iti_issue_id[0], kwargs)

      issue = db.session.query(models.IssuetrackerIssue).get(iti.id)
      self.assertEqual(issue.assignee, email1)
      self.assertEqual(issue.cc_list, "")

  def test_collect_audit_emails(self):
    """Test _collect_audit_emails function."""
    audit_captains = factories.PersonFactory.create_batch(3)
    auditors = factories.PersonFactory.create_batch(3)

    audit_captain_role_id = all_models.AccessControlRole.query.filter(
        all_models.AccessControlRole.name == "Audit Captains",
        all_models.AccessControlRole.object_type == "Audit",
    ).one().id
    auditor_role_id = all_models.AccessControlRole.query.filter(
        all_models.AccessControlRole.name == "Auditors",
        all_models.AccessControlRole.object_type == "Audit",
    ).one().id

    acl_data = self._prepare_acl(
        {
            audit_captain_role_id: audit_captains,
            auditor_role_id: auditors
        }
    )
    with app.app_context():
      # pylint: disable=protected-access
      reporter_email, cc_list = assessment_integration._collect_audit_emails(
          acl_data
      )
    audit_reporter = audit_captains[0].email
    audit_ccs = set(captain.email for captain in audit_captains[1:])
    self.assertEquals(reporter_email, audit_reporter)
    self.assertEquals(set(cc_list), audit_ccs)

  def test_audit_emails_wh_captains(self):
    """Test _collect_audit_emails without Audit Captains."""
    auditors = factories.PersonFactory.create_batch(3)
    auditor_role_id = all_models.AccessControlRole.query.filter(
        all_models.AccessControlRole.name == "Auditors",
        all_models.AccessControlRole.object_type == "Audit",
    ).one().id

    acl_data = self._prepare_acl(
        {
            auditor_role_id: auditors,
        }
    )
    with app.app_context():
      # pylint: disable=protected-access
      reporter_email, cc_list = assessment_integration._collect_audit_emails(
          acl_data
      )
    self.assertEquals(reporter_email, "")
    self.assertEquals(cc_list, [])

  def test_audit_emails_wh_auditors(self):
    """Test _collect_audit_emails without Auditors."""
    audit_captains = factories.PersonFactory.create_batch(3)
    audit_captain_role_id = all_models.AccessControlRole.query.filter(
        all_models.AccessControlRole.name == "Audit Captains",
        all_models.AccessControlRole.object_type == "Audit",
    ).one().id

    acl_data = self._prepare_acl(
        {
            audit_captain_role_id: audit_captains
        }
    )
    with app.app_context():
      # pylint: disable=protected-access
      reporter_email, cc_list = assessment_integration._collect_audit_emails(
          acl_data
      )
    audit_reporter = audit_captains[0].email
    audit_ccs = set(captain.email for captain in audit_captains[1:])
    self.assertEquals(reporter_email, audit_reporter)
    self.assertEquals(set(cc_list), audit_ccs)

  @staticmethod
  def _prepare_acl(configurations):
    """Prepare ACL payload.
    Args:
      - configurations: Dictionary with key - ACR id,
      and value - list of persons regarding ACR id
    Returns:
      -
    """
    acl_data = [
        {
            "ac_role_id": role_id,
            "person": {"id": person.id, "type": "Person"}
        } for role_id, persons in configurations.items()
        for person in persons
    ]
    return acl_data

  @mock.patch('ggrc.integrations.issues.Client.create_issue')
  @mock.patch('ggrc.integrations.issues.Client.update_issue')
  @mock.patch.object(settings, "ISSUE_TRACKER_ENABLED", True)
  def test_basic_import(self, mock_create_issue, mock_update_issue):
    """Test basic import functionality."""
    with mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                           return_value=True):
      # update existing object
      iti = factories.IssueTrackerIssueFactory(enabled=True)
      asmt = iti.issue_tracked_obj
      audit = asmt.audit
      response = self.import_data(OrderedDict([
          ('object_type', 'Assessment'),
          ('Code*', asmt.slug),
          ('Audit', audit.slug),
      ]))
      self._check_csv_response(response, {})

      # import new object
      response = self.import_data(OrderedDict([
          ('object_type', 'Assessment'),
          ('Code*', 'Test Code'),
          ('Audit', audit.slug),
          ('Creators', 'user@example.com'),
          ('Assignees*', 'user@example.com'),
          ('Title', 'Some Title'),
      ]))
      self._check_csv_response(response, {})

  @mock.patch('ggrc.integrations.issues.Client.create_issue')
  @mock.patch.object(settings, "ISSUE_TRACKER_ENABLED", True)
  def test_audit_delete(self, mock_create_issue):
    """Test deletion of an audit."""
    with mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                           return_value=True):
      audit = factories.AuditFactory()
      factories.IssueTrackerIssueFactory(
          issue_tracked_obj=audit,
          component_id="some id",
          hotlist_id="some host id",
      )
      result = self.api.delete(audit)
      self.assert200(result)

      audit = factories.AuditFactory()
      factories.IssueTrackerIssueFactory(
          issue_tracked_obj=audit,
          component_id="some id",
          hotlist_id="some host id",
      )
      result = self.api.delete(audit)
      self.assert200(result)

  @mock.patch("ggrc.integrations.issues.Client.update_issue")
  @mock.patch.object(settings, "ISSUE_TRACKER_ENABLED", True)
  def test_update_ccs_many_audit_captains(self, mock_update_issue):
    """CCS of assessment should include secondary audit captains."""
    with mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                           return_value=True):
      audit = factories.AuditFactory()
      audit_captains = factories.PersonFactory.create_batch(2)
      audit_captain_role = all_models.AccessControlRole.query.filter_by(
          name="Audit Captains",
          object_type="Audit"
      ).one()
      response_audit = self.api.put(
          audit,
          {
              "access_control_list": [
                  {
                      "ac_role_id": audit_captain_role.id,
                      "person": {
                          "id": audit_captain.id,
                          "type": "Person"
                      }
                  } for audit_captain in audit_captains]
          }
      )
      self.assert200(response_audit)
      issue_tracker_audit = all_models.IssuetrackerIssue.query.filter_by(
          object_id=audit.id,
          object_type=audit.type
      ).one()
      audit_cc = issue_tracker_audit.cc_list
      self.assertEqual(
          audit_cc,
          audit_captains[1].email
      )

      assessment = factories.AssessmentFactory(
          audit=audit
      )
      assessment_issue = factories.IssueTrackerIssueFactory(
          enabled=True,
          issue_tracked_obj=assessment,
          component_id="11111",
          hotlist_id="222222",
      )
      assessment_persons = factories.PersonFactory.create_batch(3)
      assignee_role = all_models.AccessControlRole.query.filter_by(
          name="Assignees",
          object_type="Assessment"
      ).one()
      creator_role = all_models.AccessControlRole.query.filter_by(
          name="Creators",
          object_type="Assessment"
      ).one()
      response_assessment = self.api.put(
          assessment,
          {
              "issue_tracker": {
                  "component_id": "11111",
                  "enabled": True,
                  "hotlist_id": "222222",
                  "issue_priority": "P2",
                  "issue_severity": "S2",
                  "issue_type": "PROCESS",
                  "issue_id": assessment_issue.issue_id
              },
              "access_control_list": [
                  {
                      "ac_role_id": creator_role.id
                      if not index else assignee_role.id,
                      "id": index + 1,
                      "person": {
                          "context_id": None,
                          "href": "/api/people/{}".format(
                              person.id
                          ),
                          "id": person.id,
                          "type": "Person"
                      },
                      "person_email": person.email,
                      "person_id": person.id,
                      "person_name": person.name,
                      "type": "AccessControlList"
                  }
                  for index, person in enumerate(assessment_persons)]
          }
      )
      self.assert200(response_assessment)
      issue_tracker_assessment = all_models.IssuetrackerIssue.query.filter_by(
          object_id=assessment.id,
          object_type=assessment.type
      ).one()
      issue_tracker_cc = issue_tracker_assessment.cc_list.split(',')[0]
      assessment_emails = [person.email for person in assessment_persons]
      self.assertIn(issue_tracker_cc, assessment_emails)


@mock.patch('ggrc.models.hooks.issue_tracker.'
            'assessment_integration._is_issue_tracker_enabled',
            return_value=True)
@mock.patch.object(settings, "ISSUE_TRACKER_ENABLED", True)
@mock.patch('ggrc.integrations.issues.Client')
class TestIssueTrackerIntegrationPeople(SnapshotterBaseTestCase):
  """Test people used in IssueTracker Issues."""

  EMAILS = {
      ("Audit", "Audit Captains"): {
          "audit_captain_1@example.com",
          "audit_captain_2@example.com"
      },
      ("Audit", "Auditors"): {
          "auditor_1@example.com",
          "auditor_2@example.com"
      },
      ("Assessment", "Creators"): {
          "creator_1@example.com",
          "creator_2@example.com"
      },
      ("Assessment", "Assignees"): {
          "assignee_1@example.com",
          "assignee_2@example.com"
      },
      ("Assessment", "Verifiers"): {
          "verifier_1@example.com",
          "verifier_2@example.com"
      },
      ("Assessment", "Custom Role"): {
          "curom_role_1@example.com"
      },
      ("Assessment", "Primary Contacts"): {
          "primary_contact_1@example.com",
          "primary_contact_2@example.com"
      },
      ("Assessment", "Secondary Contacts"): {
          "secondary_contact_1@example.com",
          "secondary_contact_2@example.com"
      },
  }

  ROLE_NAMES = (
      'Creators',
      'Assignees',
      'Verifiers',
      'Primary Contacts',
      'Secondary Contacts',
      'Custom Role'
  )

  def setUp(self):
    super(TestIssueTrackerIntegrationPeople, self).setUp()
    self.generator = generator.ObjectGenerator()

    factories.AccessControlRoleFactory(
        name='Custom Role',
        internal=False,
        object_type='Assessment',
    )

    # fetch all roles mentioned in self.EMAILS
    self.roles = {
        role.name: role
        for role in all_models.AccessControlRole.query.filter(
            sa.tuple_(
                all_models.AccessControlRole.object_type,
                all_models.AccessControlRole.name,
            ).in_(
                self.EMAILS.keys(),
            ),
        )
    }

    with factories.single_commit():
      self.audit = factories.AuditFactory()

      self.people = {
          role_name: [factories.PersonFactory(email=email)
                      for email in emails]
          for (_, role_name), emails in self.EMAILS.iteritems()
      }

  def setup_audit_people(self, role_name_to_people):
    """Assign roles to people provided."""
    with factories.single_commit():
      for role_name, people in role_name_to_people.iteritems():
        role = self.roles[role_name]
        for person in people:
          factories.AccessControlListFactory(person=person,
                                             ac_role=role,
                                             object=self.audit)

  def create_asmt_with_issue_tracker(self, role_name_to_people,
                                     issue_tracker=None):
    """Create Assessment with issue_tracker parameters and ACL."""
    access_control_list = acl_helper.get_acl_list({
        person.id: self.roles[role_name].id
        for role_name, people in role_name_to_people.iteritems()
        for person in people
    })
    issue_tracker_with_defaults = {
        'enabled': True,
        'component_id': hash('Default Component id'),
        'hotlist_id': hash('Default Hotlist id'),
        'issue_type': 'Default Issue type',
        'issue_priority': 'Default Issue priority',
        'issue_severity': 'Default Issue severity',
    }
    issue_tracker_with_defaults.update(issue_tracker or {})

    _, asmt = self.generator.generate_object(
        all_models.Assessment,
        data={
            'audit': {'id': self.audit.id, 'type': self.audit.type},
            'issue_tracker': issue_tracker_with_defaults,
            'access_control_list': access_control_list,
        }
    )

    return asmt

  def test_new_assessment_people(self, client_mock, _):
    """External Issue for Assessment contains correct people."""
    client_instance = client_mock.return_value
    client_instance.create_issue.return_value = {'issueId': 42}

    self.setup_audit_people({
        role_name: people for role_name, people in self.people.items()
        if role_name in ('Audit Captains', 'Auditors')
    })

    component_id = hash('Component id')
    hotlist_id = hash('Hotlist id')
    issue_type = 'Issue type'
    issue_priority = 'Issue priority'
    issue_severity = 'Issue severity'

    asmt = self.create_asmt_with_issue_tracker(
        role_name_to_people={
            role_name: people for role_name, people in self.people.items()
            if role_name in self.ROLE_NAMES
        },
        issue_tracker={
            'component_id': component_id,
            'hotlist_id': hotlist_id,
            'issue_type': issue_type,
            'issue_priority': issue_priority,
            'issue_severity': issue_severity,
        },
    )

    expected_cc_list = list(
        self.EMAILS["Assessment", "Assignees"] -
        {min(self.EMAILS["Assessment", "Assignees"])}
    )

    # pylint: disable=protected-access; we assert by non-exported constants
    client_instance.create_issue.assert_called_once_with({
        # common fields
        'comment': (assessment_integration._INITIAL_COMMENT_TMPL %
                    assessment_integration._get_assessment_url(asmt)),
        'component_id': component_id,
        'hotlist_ids': [hotlist_id],
        'priority': issue_priority,
        'severity': issue_severity,
        'status': 'ASSIGNED',
        'title': asmt.title,
        'type': issue_type,

        # person-related fields
        'reporter': min(self.EMAILS["Audit", "Audit Captains"]),
        'assignee': min(self.EMAILS["Assessment", "Assignees"]),
        'verifier': min(self.EMAILS["Assessment", "Assignees"]),
        'ccs': expected_cc_list,
    })

  def test_missing_audit_captains(self, client_mock, _):
    """Reporter email is None is no Audit Captains present."""
    client_instance = client_mock.return_value
    client_instance.create_issue.return_value = {'issueId': 42}

    self.setup_audit_people({
        'Audit Captains': [],
        'Auditors': self.people['Auditors'],
    })

    self.create_asmt_with_issue_tracker(
        role_name_to_people={
            role_name: people for role_name, people in self.people.items()
            if role_name in ('Creators', 'Assignees', 'Verifiers')
        },
    )

    client_instance.create_issue.assert_called_once()
    self.assertIs(client_instance.create_issue.call_args[0][0]['reporter'],
                  None)
