# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Date utils."""
import datetime

import holidays


def first_not_weekend_day(date):
  """Returns the nearest not weekend day today or in past.
  Used for a datepicker that does not allow to choose weekends.
  """
  while _is_weekend(date):
    date += datetime.timedelta(days=-1)
  return date


def first_working_day(date):
  """Returns the nearest working day today or in past.
  This algorithm is used when back-end generates a cycle task.
  """
  while _is_weekend(date) or date in holidays.UnitedStates():
    date += datetime.timedelta(days=-1)
  return date


def _is_weekend(date):
  """Returns whether the date is a weekend."""
  return date.isoweekday() in (6, 7)  # Saturday, Sunday


def str_to_date(date_str, date_format):
  """Converts string in format `format` to date."""
  return str_to_datetime(date_str, date_format).date()


def str_to_datetime(datetime_str, datetime_format):
  """Converts string in format to datetime."""
  return datetime.datetime.strptime(datetime_str, datetime_format)
