# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Add new columns to ctgot table

Create Date: 2018-10-30 11:44:39.104118
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

from alembic import op

revision = '87bcc96974cd'
down_revision = '871aaab0de41'


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  sql = """
    ALTER TABLE cycle_task_group_object_tasks
      ADD recipients varchar(250)
        DEFAULT 'Task Assignee,Task Secondary Assignee',
      ADD send_by_default tinyint(1) DEFAULT '1'
  """
  op.execute(sql)


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
  raise Exception("Downgrade is not supported.")
