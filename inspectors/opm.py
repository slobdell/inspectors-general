#!/usr/bin/env python

from utils import utils, inspector
from bs4 import BeautifulSoup
import bs4
import os
import logging
import time
import calendar

archive = 1998

#  Note: reports are only scraped from /our-inspector-general/reports/
#  I think this is mostly just audit reports (other reports are scattered
#  around the website

#  options
#    --since=[year] fetches all reports from that year to now
#    --year=[year] fetches all reports for a particular year
#
#    defaults to current year.
#
#    --report_id   limit it to a specific report ID (since/year should include it)

# previously ignored: 4A-CI-00-14-015
BLACKLIST = ()

def run(options):
  year_range = inspector.year_range(options, archive)
  only_id = options.get('report_id')

  logging.info("## Downloading reports from %i to %i" % (year_range[0], year_range[-1]))

  url = url_for()
  body = utils.download(url)

  doc = BeautifulSoup(body)
  results = doc.select("section")

  for result in results:
    try:
      year = int(result.get("title"))
      # check that the fetched year is in the range
      if year not in year_range:
        continue
      logging.info("## Downloading year %i " % year)
    except ValueError:
      continue

    # gets each table entry and sends generates a report from it
    listings = result.div.table.tbody.contents
    for item in listings:
      if type(item) is not bs4.element.Tag:
        continue
      report = report_from(item)

      if report['report_id'] in BLACKLIST:
        logging.warn("Skipping downed report: remember to report this and get it fixed!")
        continue

      # can limit it to just one report, for debugging convenience
      if only_id and only_id != report['report_id']:
        continue

      inspector.save_report(report)

def url_for():
  cache_buster = str(int(time.time()))
  return "https://www.opm.gov/our-inspector-general/reports/?t=%s" % cache_buster

#  generates the report item from a table item
def report_from(item):
  report = {
    'inspector': 'opm',
    'inspector_url': 'https://www.opm.gov/our-inspector-general/',
    'agency': 'opm',
    'agency_name': 'U.S. Office of Personnel Management'
  }

  # date can sometimes be surrounded with <span>
  raw_date = item.th.text

  if type(raw_date) is bs4.element.Tag:
    raw_date = raw_date.text
  raw_date = raw_date.split(" ")

  month = str(find_month_num(raw_date[0]))
  day = raw_date[1].replace(",", "")
  year = raw_date[2]

  report['published_on'] = "%04d-%02d-%02d" % (int(year), int(month), int(day))

  raw_link = item.find_all('td')[0].a
  report['url'] = 'https://www.opm.gov' + raw_link.get('href')
  report['title'] = raw_link.text.strip()

  if 'audit' not in report['title'].lower():
    report['type'] = 'other'

  raw_id = None
  try:
    raw_id = item.find_all('td')[1].contents[0]
    if type(raw_id) is bs4.element.Tag:
      while raw_id.span:
        raw_id = raw_id.span
      raw_id = raw_id.string
  except IndexError:
    pass

  # if the document doesn't have a listed id - use slug of name, stored at a[title]
  if (raw_id is None) or (raw_id.strip() == ""):
    raw_id = raw_link.get("title")
    if not raw_id:
      filename = os.path.basename(raw_link.get('href'))
      raw_id = os.path.splitext(filename)[0]

  report['report_id'] = raw_id

  return report


def find_month_num(month):
  for i in range(len(calendar.month_name)):
    if month == calendar.month_name[i]:
      return i
  return -1


utils.run(run) if (__name__ == "__main__") else None
