# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Tests basic wf cycle tasks notifications generation logic."""

# pylint: disable=invalid-name

from datetime import datetime
from datetime import timedelta
from datetime import date

from freezegun import freeze_time

from ggrc.models import Notification
from ggrc.models import all_models
from ggrc.notifications.common import generate_cycle_tasks_notifs
from integration.ggrc import TestCase
from integration.ggrc_workflows.helpers import workflow_api

from integration.ggrc.api_helper import Api
from integration.ggrc.generator import ObjectGenerator
from integration.ggrc_workflows.generator import WorkflowsGenerator
from integration.ggrc.models import factories
from integration.ggrc_workflows.models import factories as wf_factories


class TestWfNotifsGenerator(TestCase):
  """Test wf cycle tasks notifications generation."""
  def setUp(self):
    """Set up."""
    super(TestWfNotifsGenerator, self).setUp()
    self.api = Api()
    self.wf_generator = WorkflowsGenerator()
    self.object_generator = ObjectGenerator()
    Notification.query.delete()

    with freeze_time("2015-05-01 14:29:00"):
      wf_slug = "wf1"
      with factories.single_commit():
        wf = wf_factories.WorkflowFactory(slug=wf_slug)
        task_group = wf_factories.TaskGroupFactory(workflow=wf)
        wf_factories.TaskGroupTaskFactory(
            task_group=task_group,
            title='task1',
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(7)
        )
      data = workflow_api.get_cycle_post_dict(wf)
      self.api.post(all_models.Cycle, data)
      wf = all_models.Workflow.query.filter_by(slug=wf_slug).one()
      self.cycle = all_models.Cycle.query.filter_by(workflow_id=wf.id).one()
      self.ctask = all_models.CycleTaskGroupObjectTask.query.filter_by(
          cycle_id=self.cycle.id).first()

  def test_ctasks_notifs_generator_daily_digest(self):
    """Test cycle tasks notifications generation job."""
    with freeze_time("2015-05-01 14:29:00"):
      generate_cycle_tasks_notifs(date(2015, 5, 1))
      self.assert_notifications_for_object(self.cycle, "manual_cycle_created")
      self.assert_notifications_for_object(self.ctask,
                                           "manual_cycle_created",
                                           "cycle_task_due_in",
                                           "cycle_task_due_today",
                                           "cycle_task_overdue")

      # Move task to Finished
      self.wf_generator.modify_object(
          self.ctask, data={"status": "Verified"})
      generate_cycle_tasks_notifs(date(2015, 5, 1))
      self.assert_notifications_for_object(self.cycle,
                                           "all_cycle_tasks_completed",
                                           "manual_cycle_created")

      # Undo finish
      self.wf_generator.modify_object(
          self.ctask, data={"status": "In Progress"})
      generate_cycle_tasks_notifs(date(2015, 5, 1))
      self.assert_notifications_for_object(self.cycle, "manual_cycle_created")
      self.assert_notifications_for_object(self.ctask,
                                           "cycle_task_due_in",
                                           "cycle_task_due_today",
                                           "cycle_task_overdue")

      self.wf_generator.modify_object(
          self.ctask, data={"status": "Declined"})
      self.assert_notifications_for_object(self.ctask,
                                           "cycle_task_due_in",
                                           "cycle_task_due_today",
                                           "cycle_task_overdue",
                                           "cycle_task_declined")

  def test_ctasks_notifs_generator_daily_digest_called_twice(self):
    """No duplicated notifications should be generated"""
    with freeze_time("2015-05-01 14:29:00"):
      generate_cycle_tasks_notifs(date(2015, 5, 1))
      self.assert_notifications_for_object(self.cycle, "manual_cycle_created")
      self.assert_notifications_for_object(self.ctask,
                                           "manual_cycle_created",
                                           "cycle_task_due_in",
                                           "cycle_task_due_today",
                                           "cycle_task_overdue")

      # Move task to Finished
      self.wf_generator.modify_object(
          self.ctask, data={"status": "Verified"})
      generate_cycle_tasks_notifs(date(2015, 5, 1))
      generate_cycle_tasks_notifs(date(2015, 5, 1))
      self.assert_notifications_for_object(self.cycle,
                                           "all_cycle_tasks_completed",
                                           "manual_cycle_created")

  def test_ctasks_notifs_generator_cron_job(self):
    """Test cycle tasks notifications generation cron job."""
    with freeze_time("2015-05-2 08:00:00"):
      generate_cycle_tasks_notifs()
      self.assert_notifications_for_object(self.cycle, "manual_cycle_created")
      self.assert_notifications_for_object(self.ctask,
                                           "manual_cycle_created",
                                           "cycle_task_due_in",
                                           "cycle_task_due_today",
                                           "cycle_task_overdue")
