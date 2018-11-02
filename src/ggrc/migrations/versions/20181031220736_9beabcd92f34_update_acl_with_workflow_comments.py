# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Update acl with workflow comments

Create Date: 2018-10-31 22:07:36.958777
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name


from ggrc.migrations.utils.acr_propagation import update_acr_propagation_tree
from ggrc.migrations.utils import acr_propagation_constants_workflow_comments

revision = '9beabcd92f34'
down_revision = '87bcc96974cd'


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  update_acr_propagation_tree(
      acr_propagation_constants_workflow_comments.CURRENT_PROPAGATION,
      new_tree=acr_propagation_constants_workflow_comments.WORKFLOW_PROPAGATION
  )


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
