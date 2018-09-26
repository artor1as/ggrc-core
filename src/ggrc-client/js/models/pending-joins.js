/*
  Copyright (C) 2018 Google Inc.
  Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import Stub from './stub';
import * as mappingModels from '../models/mapping-models';
import Mappings from '../models/mappers/mappings';

const resolveDeferredBindings = (obj) => {
  const hasPendingJoins = _.get(obj, '_pending_joins.length') > 0;

  if (!hasPendingJoins) {
    return can.Deferred().resolve(obj);
  }

  return _resolveDeferredBindings(obj)
    .then(() => obj.refresh());
};

function _resolveDeferredBindings(obj) {
  const pendingJoins = obj._pending_joins.slice(0); // refresh of bindings later will muck up the pending joins on the object
  const uniqueThrough = _(pendingJoins).chain()
    .map((pj) => pj.through)
    .uniq()
    .value();

  const refreshDfds = [];
  can.each(uniqueThrough, (binding) => {
    refreshDfds.push(Mappings.get_binding(binding, obj).refresh_stubs());
  });

  return $.when(...refreshDfds)
    .then(() => {
      const dfds = [];
      can.each(obj._pending_joins, (pj) => {
        switch (pj.how) {
          case 'add':
            dfds.push(..._addHandler(obj, pj));
            break;
          case 'remove':
            dfds.push(..._removeHandler(obj, pj));
            break;
          default: {
            // nothing
          }
        }
      });

      const dfdsApply = $.when(...dfds);
      obj.attr('_pending_joins', []);
      obj.attr('_pending_joins_dfd', dfdsApply);

      return dfdsApply.then(() => {
        obj.dispatch('resolvePendingBindings');
        return obj;
      });
    });
}

function _addHandler(obj, pj) {
  const binding = Mappings.get_binding(pj.through, obj);
  const dfds = [];
  // Don't re-add -- if the object is already mapped (could be direct or through a proxy)
  // move on to the next one
  if (_.includes(_.map(binding.list, 'instance'), pj.what) ||
      (binding.loader.option_attr &&
      _.includes(_.map(binding.list, function (joinObj) {
        return joinObj.instance[binding.loader.option_attr];
      }), pj.what))) {
    return dfds;
  }
  const model = mappingModels[binding.loader.model_name];
  const inst = pj.what instanceof model
    ? pj.what
    : new model({
      context: obj.context,
    });
  const pjDfd = pj.what !== inst && pj.what.isNew()
    ? pj.what.save() : null;
  const dfd = $.when(pjDfd)
    .then(function () {
      if (binding.loader.object_attr) {
        inst.attr(binding.loader.object_attr, new Stub(obj));
      }
      if (binding.loader.option_attr) {
        inst.attr(binding.loader.option_attr, new Stub(pj.what));
      }
      if (pj.extra) {
        inst.attr(pj.extra);
      }
      return inst.save();
    });
  dfds.push(dfd);
  return dfds;
}

function _removeHandler(obj, pj) {
  const binding = Mappings.get_binding(pj.through, obj);
  const dfds = [];
  can.map(binding.list, function (boundObj) {
    let blOptionAttr = binding.loader.option_attr;
    if (boundObj.instance === pj.what ||
        boundObj.instance[blOptionAttr] === pj.what) {
      can.each(boundObj.get_mappings(), function (mapping) {
        dfds.push(mapping.refresh().then(function () {
          mapping.destroy();
        }));
      });
    }
  });
  return dfds;
}

export {resolveDeferredBindings};
