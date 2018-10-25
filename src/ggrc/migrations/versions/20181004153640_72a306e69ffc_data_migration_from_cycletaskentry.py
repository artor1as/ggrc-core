# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Data migration from CycleTaskEntry into Comments table

Create Date: 2018-10-04 15:36:40.842930
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

from sqlalchemy import text
from alembic import op
from ggrc.migrations import utils


# revision identifiers, used by Alembic.
from ggrc.migrations.utils import add_to_objects_without_revisions

revision = '72a306e69ffc'
down_revision = 'cb58d1d52368'


def get_cycle_task_entries(conn):
  """Get all cycle_task_entries from database"""
  sql = """
    SELECT 
      id, 
      description, 
      created_at, 
      modified_by_id, 
      updated_at, 
      context_id 
    FROM 
      cycle_task_entries
    """
  return conn.execute(text(sql))


def get_cte_relationship_sources(conn, destination_id):
  """Get relationships source_id and source_type for cte by destination_id"""
  sql = """
    SELECT 
      id, source_id, source_type 
    FROM 
      relationships 
    WHERE 
      destination_id = :destination_id 
        AND 
          destination_type = 'CycleTaskEntry'
  """
  return conn.execute(text(sql), destination_id=destination_id).first()


def replace_cte_relationships(conn, source_id, source_type, destination_id,
                              destination_type):
  """Replace cte relationships with new between comments and ctgot"""
  sql = """
    INSERT INTO relationships (
      created_at, 
      updated_at, 
      source_id, 
      source_type, 
      destination_id, 
      destination_type
    ) VALUES (
      NOW(), NOW(), :source_id, :source_type, :destination_id, 
      :destination_type
    )
  """
  conn.execute(
    text(sql),
    source_id=source_id,
    source_type=source_type,
    destination_id=destination_id,
    destination_type=destination_type,
  )
  relationship_id = utils.last_insert_id(conn)
  utils.add_to_objects_without_revisions(conn, relationship_id, 'Relationship')


def cycle_task_entry_data_migrate(conn):
  """Migrate data from cte to comments table and create new revisions"""
  for data in get_cycle_task_entries(conn):
    sql = """
      INSERT INTO comments (
        description, 
        created_at, 
        modified_by_id, 
        updated_at,
        context_id
      ) VALUES (
       :description, :created_at, :modified_by_id, :updated_at, :context_id
       )
       """
    conn.execute(
      text(sql),
      description=data.description,
      created_at=data.created_at,
      modified_by_id=data.modified_by_id,
      updated_at=data.updated_at,
      context_id=data.context_id
    )
    comment_id = utils.last_insert_id(conn)
    cte_relationship = get_cte_relationship_sources(conn, data.id)
    replace_cte_relationships(
      conn=conn,
      source_id=cte_relationship.source_id,
      source_type=cte_relationship.source_type,
      destination_id=comment_id,
      destination_type='Comment'
    )
    utils.add_to_objects_without_revisions(conn, comment_id, "Comment")


def add_columns_to_ctgot_table(conn):
  """Add two new columns to """
  sql = """
    ALTER TABLE cycle_task_group_object_tasks
      ADD recipients varchar(250) 
        DEFAULT 'Task Assignee,Task Secondary Assignee',
      ADD send_by_default tinyint(1) DEFAULT '1'
  """
  conn.execute(text(sql))


def run_migrations():
  """Migration runner"""
  conn = op.get_bind()
  cycle_task_entry_data_migrate(conn)
  add_columns_to_ctgot_table(conn)


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  run_migrations()


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
