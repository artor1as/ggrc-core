# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

from datetime import datetime

from mock import patch
from sqlalchemy import and_

from ggrc import db
from ggrc.access_control.role import get_custom_roles_for
from ggrc.notifications import common
from ggrc.models import all_models
from ggrc.models import Notification
from ggrc.models import NotificationType
from integration.ggrc.models import factories
from integration.ggrc_workflows.models import factories as wf_factories
from integration.ggrc import generator, TestCase


class TestWorkflowCommentNotification(TestCase):

  def setUp(self):
    super(TestWorkflowCommentNotification, self).setUp()
    self.client.get("/login")
    self._fix_notification_init()
    self.generator = generator.ObjectGenerator()

  def _fix_notification_init(self):
    """Fix Notification object init function.

    This is a fix needed for correct created_at field when using freezgun. By
    default the created_at field is left empty and filed by database, which
    uses system time and not the fake date set by freezugun plugin. This fix
    makes sure that object created in feeze_time block has all dates set with
    the correct date and time.
    """

    def init_decorator(init):
      """Wrapper for Notification init function."""

      def new_init(self, *args, **kwargs):
        init(self, *args, **kwargs)
        if hasattr(self, "created_at"):
          self.created_at = datetime.now()
      return new_init

    Notification.__init__ = init_decorator(Notification.__init__)

  @classmethod
  def _get_notifications(cls, sent=False, notif_type=None):
    """Get a notification query.

    Args:
      sent (boolean): flag to filter out only notifications that have been
        sent.
      notif_type (string): name of the notification type.

    Returns:
      sqlalchemy query for selected notifications.
    """
    if sent:
      notif_filter = Notification.sent_at.isnot(None)
    else:
      notif_filter = Notification.sent_at.is_(None)

    if notif_type:
      notif_filter = and_(notif_filter, NotificationType.name == notif_type)

    return db.session.query(Notification).join(NotificationType).filter(
      notif_filter
    )

  @patch("ggrc.notifications.common.send_email")
  def test_ctgot_comments(self, _):
    """Test setting notification entries for ctgot comments.

    Check if the correct notification entries are created when a comment gets
    posted.
    """
    recipient_types = ["Task Assignees", "Task Secondary Assignees"]
    person = all_models.Person.query.first()
    person_email = person.email
    with factories.single_commit():
      obj = wf_factories.CycleTaskFactory(
        recipients=",".join(recipient_types),
        send_by_default=False,
      )
      ac_roles = get_custom_roles_for(obj.type)
      for acr_id, acr_name in ac_roles.items():
        if acr_name in recipient_types:
          import ipdb; ipdb.set_trace()
          factories.AccessControlListFactory(
            ac_role_id=acr_id, object=obj, person=person
          )

    self.generator.generate_comment(
      obj, "", "some comment", send_notification="true")

    notifications, notif_data = common.get_daily_notifications()
    self.assertEqual(len(notifications), 1,
                     "Missing comment notification entry.")

    recip_notifs = notif_data.get(person_email, {})
    comment_notifs = recip_notifs.get("comment_created", {})
    self.assertEqual(len(comment_notifs), 1)

    self.client.get("/_notifications/send_daily_digest")
    notifications = self._get_notifications(notif_type="comment_created").all()
    self.assertEqual(len(notifications), 0,
                     "Found a comment notification that was not sent.")
