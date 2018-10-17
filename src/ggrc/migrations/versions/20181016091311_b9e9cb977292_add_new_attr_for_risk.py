# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Add new attr for risk

Create Date: 2018-10-16 09:13:11.400235
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

from alembic import op


# revision identifiers, used by Alembic.
revision = 'b9e9cb977292'
down_revision = 'cb58d1d52368'


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  sql = """
    ALTER TABLE risks
    ADD risk_type text NOT NULL,
    ADD threat_source text NULL,
    ADD threat_event text NULL,
    ADD vulnerability text NULL
  """
  op.execute(sql)


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
  sql = """
    ALTER TABLE risks
    DROP risk_type,
    DROP threat_source,
    DROP threat_event,
    DROP vulnerability
  """
  op.execute(sql)
