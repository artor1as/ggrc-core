/*
  Copyright (C) 2018 Google Inc.
  Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import Component from '../modal-connector';
import {getComponentVM} from '../../../js_specs/spec_helpers';

describe('ggrc-modal-connector component', function () {
  let viewModel;
  let events;

  beforeAll(function () {
    events = Component.prototype.events;
  });
  beforeEach(function () {
    viewModel = getComponentVM(Component);
  });
  describe('init() method', function () {
    let handler;

    beforeEach(function () {
      handler = events.init.bind({viewModel});
    });

    it('sets instance of component to viewModel.controller', function () {
      handler();
      expect(viewModel.attr('controller').viewModel)
        .toEqual(viewModel);
    });
  });

  describe('addMappings() method', function () {
    beforeEach(() => {
      viewModel.attr('changes', []);
      spyOn(viewModel, 'addListItem');
    });
    it('adds add-change to viewModel.changes if it is deferred',
      function () {
        const objects = [
          new can.Map({id: 0}),
          new can.Map({id: 1}),
        ];
        viewModel.addMappings(objects);

        viewModel.attr('changes').each((change) => {
          expect(change).toEqual(jasmine.objectContaining({how: 'add'}));
        });
      });
  });
});
