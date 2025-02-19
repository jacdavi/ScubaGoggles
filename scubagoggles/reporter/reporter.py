"""
reporter.py creates the report html page

Currently utilizes pandas to generate the HTML table fragments
"""
import os
import time
from datetime import datetime
import pandas as pd
from scubagoggles.utils import rel_abs_path

def get_test_result(requirement_met : bool, criticality : str, no_such_events : bool) -> str:
    '''
    Checks the Rego to see if the baseline passed or failed and indicates the criticality
    of the baseline.

    :param requirement_met: a boolean value indicating if the requirement passed or failed.
    :param criticality: a string value indicating the criticality of the failed baseline,
        values: should, may, 3rd Party, Not-Implemented
    :param no_such_events: boolean whether there are no such events
    '''
    criticality = criticality.lower()
    if requirement_met:
        result = "Pass"
    elif "3rd party" in criticality or 'not-implemented' in criticality:
        result = "N/A"
    elif no_such_events:
        result = "No events found"
    elif criticality in ('should', 'may'):
        result = "Warning"
    else:
        result = "Fail"
    return result

def create_html_table(table_data : list) -> str:
    '''
    Creates an HTML Table for the results of the Rego Scan

    :param table_data: list object of results of Rego Scan
    '''
    table_html = pd.DataFrame(table_data).to_html(border = 0, index = False,
    escape=False, render_links=True)
    table_html = table_html.replace(' style="text-align: right;"', '')
    table_html = table_html.replace(' class="dataframe"', '')
    return table_html

def build_front_page_html(fragments : list, tenant_info : dict) -> str:
    '''
    Builds the Front Page Report using the HTML Report Template

    :param fragments: list object containing each baseline
    '''
    reporter_path = str(rel_abs_path(__file__,"./"))
    with open(os.path.join(reporter_path, './FrontPageReport/FrontPageReportTemplate.html'),
    mode='r', encoding='UTF-8') as file:
        html = file.read()

    table = "".join(fragments)

    with open(os.path.join(reporter_path, './styles/main.css'), mode='r', encoding='UTF-8') as file:
        css = file.read()
    html = html.replace('{{MAIN_CSS}}', f"<style>{css}</style>")

    front_page_path = os.path.join(reporter_path, './styles/FrontPageStyle.css')
    with open(front_page_path, mode='r', encoding='UTF-8') as file:
        css = file.read()
    html = html.replace('{{FRONT_CSS}}', f"<style>{css}</style>")

    html = html.replace('{{TABLE}}', table)

    now = datetime.now()
    report_date = now.strftime("%m/%d/%Y %H:%M:%S") + " " + time.tzname[time.daylight]

    meta_data = f"\
        <table style = \"text-align:center;\"> \
            <colgroup><col/><col/><col/><col/></colgroup> \
            <tr><th>Customer Domain</th><th>Report Date</th></tr> \
            <tr><td>{tenant_info['domain']}</td><td>{report_date}</td></tr> \
        </table>"
    html = html.replace('{{TENANT_DETAILS}}', meta_data)
    return html

def build_report_html(fragments : list, product : str,
tenant_domain : str, main_report_name: str) -> str:
    '''
    Adds data into HTML Template and formats the page accordingly

    :param fragments: list object containing each baseline
    :param product: str object containing name of Google Product being evaluated
    :param tenant_domain: the primary domain of the tenant.
    :param main_report_name: Name of the main report HTML file.
    '''
    reporter_path = str(rel_abs_path(__file__,"./"))
    with open(os.path.join(reporter_path, './IndividualReport/IndividualReportTemplate.html'),
    mode='r', encoding='UTF-8') as file:
        html = file.read()

    with open(os.path.join(reporter_path, './styles/main.css'), mode='r', encoding='UTF-8') as file:
        css = file.read()
    html = html.replace('{{MAIN_CSS}}', f"<style>{css}</style>")

    with open(os.path.join(reporter_path, 'scripts/main.js'), mode='r', encoding='UTF-8') as file:
        javascript = file.read()
    html = html.replace('{{MAIN_JS}}', f"<script>{javascript}</script>")

    title = product + " Baseline Report"
    html = html.replace('{{TITLE}}', title)

    # this block of code is for adding
    # warning notifications to any of the baseline reports
    classroom_notification = "<p>Note: Google Classroom is not available by default in GWS"\
    " but as an additional Google Service.</p>"
    no_warning = "<p><br/></p>"

    if product == 'Google Classroom':
        html = html.replace('{{WARNING_NOTIFICATION}}', classroom_notification)
    else:
        html = html.replace('{{WARNING_NOTIFICATION}}', no_warning)

    # Relative path back to the front page
    home_page = f'../{main_report_name}.html'
    html = html.replace('{{HOMELINK}}', home_page)

    now = datetime.now()

    report_date = now.strftime("%m/%d/%Y %H:%M:%S") + " " + time.tzname[time.daylight]
    baseline_version = "0.1"
    tool_version = "0.1.0"
    meta_data = f"\
        <table style = \"text-align:center;\"> \
            <colgroup><col/><col/><col/></colgroup> \
            <tr><th>Customer Domain </th><th>Report Date</th><th>Baseline Version</th><th>Tool Version</th></tr> \
            <tr><td>{tenant_domain}</td><td>{report_date}</td><td>{baseline_version}</td><td>{tool_version}</td></tr> \
        </table>"

    html = html.replace('{{METADATA}}', meta_data)

    collected = "".join(fragments)

    html = html.replace('{{TABLES}}', collected)
    return html

def rego_json_to_html(test_results_data : str, product : list, out_path : str,
tenant_domain : str, main_report_name : str, prod_to_fullname: dict, product_policies) -> None:
    '''
    Transforms the Rego JSON output into HTML

    :param test_results_data: json object with results of Rego test
    :param product: list of products being tested
    :param out_path: output path where HTML should be saved
    :param tenant_domain: The primary domain of the GWS org
    :param main_report_name: report_name: Name of the main report HTML file.
    :param prod_to_fullname: dict containing mapping of the product full names
    :param product_policies: dict containing policies read from the baseline markdown
    '''

    product_capitalized = product.capitalize()
    product_upper = 'DRIVEDOCS' if product == 'drive' else product.upper()
    ind_report_name =  product_capitalized + "Report.html"
    fragments = []

    report_stats = {
        "Pass": 0,
        "Warning": 0,
        "Fail": 0,
        "N/A": 0,
        "No events found": 0
    }

    for baseline_group in product_policies:
        table_data = []
        for control in baseline_group['Controls']:
            tests = [test for test in test_results_data if test['PolicyId'] == control['Id']]
            for test in tests:
                result = get_test_result(test['RequirementMet'], test['Criticality'],
                test['NoSuchEvent'])
                report_stats[result] = report_stats[result] + 1
                details = test['ReportDetails']

                if result == "No events found":
                    warning_icon = "<object data='./images/triangle-exclamation-solid.svg'\
                        width='15'\
                        height='15'>\
                        </object>"
                    details = warning_icon + " " + test['ReportDetails']

                # As rules doesn't have it's own baseline, Rules and Common Controls
                # need to be handled specially
                if product_capitalized == "Rules":
                    if 'Not-Implemented' in test['Criticality']:
                        # The easiest way to identify the GWS.COMMONCONTROLS.14.1v1
                        # results that belong to the Common Controls report is they're
                        # marked as Not-Implemented. This if excludes them from the
                        # rules report.
                        continue
                    table_data.append({
                        'Control ID': control['Id'],
                        'Rule Name': test['Requirement'],
                        'Result': result,
                        'Criticality': test['Criticality'],
                        'Rule Description': test['ReportDetails']})
                elif product_capitalized == "Commoncontrols" \
                    and baseline_group['GroupName'] == 'System-defined Rules' \
                    and 'Not-Implemented' not in test['Criticality']:
                    # The easiest way to identify the System-defined Rules
                    # results that belong to the Common Controls report is they're
                    # marked as Not-Implemented. This if excludes the full results
                    # from the Common Controls report.
                    continue
                else:
                    table_data.append({
                    'Control ID': control['Id'],
                    'Requirement': control['Value'],
                    'Result': result,
                    'Criticality': test['Criticality'],
                    'Details': details})
        fragments.append(f"<h2>{product_upper}-{baseline_group['GroupNumber']} \
        {baseline_group['GroupName']}</h2>")
        fragments.append(create_html_table(table_data))
    html = build_report_html(fragments, prod_to_fullname[product], tenant_domain, main_report_name)
    with open(f"{out_path}/IndividualReports/{ind_report_name}",
    mode='w', encoding='UTF-8') as file:
        file.write(html)
    return report_stats
