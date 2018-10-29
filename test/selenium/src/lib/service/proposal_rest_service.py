# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Services for create and manipulate Proposal objects via Rest."""
from dateutil import parser, tz
from lib import url
from lib.constants import objects
from lib.service import rest_service
from lib.service.rest import query


class ProposalsService(rest_service.HelpRestService):
  """Class for Proposals business layer's services objects."""
  def __init__(self):
    super(ProposalsService, self).__init__(url.QUERY)

  def get_obj_proposals(self, obj):
    """Get and return object proposals according to obj type and id."""
    return rest_service.BaseRestService.get_items_from_resp(
        self.client.create_object(
            type=self.endpoint,
            object_name=objects.get_obj_type(objects.PROPOSALS),
            filters=query.Query.expression_get_obj_proposals(obj.type, obj.id),
            order_by=[
                {"name": "status", "desc": True},
                {"name": "created_at", "desc": True}])).get("values")

  def get_proposal_creation_date(self, obj, proposal):
    """Get proposal creation date."""
    datetime = None
    for prop in self.get_obj_proposals(obj):
      if (
          proposal.changes[0]["proposed_value"] in
          prop["content"]["fields"]["description"]
      ):
        datetime = parser.parse(prop["created_at"]).replace(tzinfo=tz.tzutc())
        break
    return datetime
