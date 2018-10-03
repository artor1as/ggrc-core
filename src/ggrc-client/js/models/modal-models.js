/*
  Copyright (C) 2018 Google Inc.
  Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import * as businessModels from './business-models';

import AccessControlRole from './custom-roles/access-control-role';
import CustomAttributeDefinition from './custom-attributes/custom-attribute-definition';

export default {
  ...businessModels,
  AccessControlRole,
  CustomAttributeDefinition,
};
