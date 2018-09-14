/*
 Copyright (C) 2018 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import RefreshQueue from '../../models/refresh_queue';
import Mappings from '../../models/mappers/mappings';
import {allowedToMap} from '../ggrc_utils';
import {backendGdriveClient} from '../ggrc-gapi-client';
import * as mappingModels from '../../models/mapping-models';

async function mapObjects(instance, objects, {
  useSnapshots,
} = {}) {
  let mapping;
  let Model;
  let data = {};
  let defer = [];
  let que = new RefreshQueue();

  return que.enqueue(instance).trigger().then(async (inst) => {
    data.context = instance.context || null;
    objects.forEach((destination) => {
      let modelInstance;
      let isAllowed;
      // Use simple Relationship Model to map Snapshot
      if (useSnapshots) {
        modelInstance = new mappingModels.Relationship({
          context: data.context,
          source: instance,
          destination: {
            href: '/api/snapshots/' + destination.id,
            type: 'Snapshot',
            id: destination.id,
          },
        });

        return defer.push(modelInstance.save());
      }

      isAllowed = allowedToMap(instance, destination);

      if (!isAllowed) {
        return;
      }
      mapping = Mappings.get_canonical_mapping(instance.type, destination.type);
      Model = mappingModels[mapping.model_name];
      data[mapping.object_attr] = {
        href: instance.href,
        type: instance.type,
        id: instance.id,
      };
      data[mapping.option_attr] = destination;
      modelInstance = new Model(data);
      defer.push(backendGdriveClient.withAuth(() => {
        return modelInstance.save();
      }));
    });

    return $.when(...defer);
  });
}

export {
  mapObjects,
};
