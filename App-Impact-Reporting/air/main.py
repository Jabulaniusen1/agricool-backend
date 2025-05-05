from flask import Flask, request, Response
import time
from air.reporters.impact_reporter import ImpactReporter
from io import BytesIO
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route("/company/<company_id>/cusers")
def get_cusers(company_id):
    """ Get excel of list of cooling users for company id
    Uses the company id to get a list of cooling users for the company
    Additionally combines this list with check in information to also provide
    check in information about each cooling user

    Args:
        company_id (int): Id of the corresponding company
        only_active (bool): Wheter to show all company cooling users or only
                            the active ones

    Returns:
        excel file: File containing list of cooling users for the company
    """

    #Set query params
    only_active = (request.args.get('only_active', default='True').lower() == 'true')

    # Get the report data frame
    reporter = ImpactReporter()
    cuser_df = reporter.get_cooling_users_report(company_id, only_active)

    # Create and return the excel
    excel_writer = BytesIO()
    cuser_df.to_excel(excel_writer, sheet_name='Sheet1', index=False)
    excel_writer.seek(0)

    filename = f'cooling_users_comp_id_{company_id}_date_{time.strftime("%y-%m-%d")}.xlsx'
    response_content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response = Response(excel_writer.read(), content_type=response_content_type)
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'

    return response

@app.route("/company/<company_id>/usage_analysis")
def get_usage_anaylsis(company_id):
    """ Get excel of list of checked-in crates for company id
    Uses the company id to get a list of crates checked in for the company
    Additionally combines this list with crop, location and user information
    to provide additional information

    Args:
        company_id (int): Id of the corresponding company
        cooling_unit_ids (str): Comma separated list of cooling unit
                                ids to filter the report on
        start_date (str) : String of format "YYY-MM-DD" to filter only
                           crates checked in after this date
        end_date (str) : String of format "YYY-MM-DD" to filter only
                           crates checked in after this date

    Returns:
        excel file: File containing list of checked in crates for company
    """

    # Set query params
    cooling_unit_ids = request.args.get('cooling_unit_ids', '')
    start_date = request.args.get('start_date', default=None)
    end_date = request.args.get('end_date', default=None)

    # Get the report data frame
    reporter = ImpactReporter()
    usage_analysis_df = reporter.get_usage_analysis_report(company_id, cooling_unit_ids,
                                                          start_date, end_date)

    # Create and return the excel
    excel_writer = BytesIO()
    usage_analysis_df.to_excel(excel_writer, sheet_name='Sheet1', index=False)
    excel_writer.seek(0)

    filename = f'usage_analysis_comp_id_{company_id}_date_{time.strftime("%y-%m-%d")}.xlsx'
    response_content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response = Response(excel_writer.read(), content_type=response_content_type)
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'

    return response

@app.route("/company/<company_id>/revenue_analysis")
def get_revenue_anaylsis(company_id):
    """ Get excel of list of checked-out crates for company id
    Uses the company id to get a list of crates checked out for the company
    Additionally combines this list with crop, location, price and user 
    information to provide additional information

    Args:
        company_id (int): Id of the corresponding company
        cooling_unit_ids (str): Comma separated list of cooling unit
                                ids to filter the report on
        start_date (str) : String of format "YYY-MM-DD" to filter only
                           crates checked in after this date
        end_date (str) : String of format "YYY-MM-DD" to filter only
                           crates checked in after this date

    Returns:
        excel file: File containing list of checked out crates for company
    """
    
    # Set query params
    cooling_unit_ids = request.args.get('cooling_unit_ids', '')
    start_date = request.args.get('start_date', default=None)
    end_date = request.args.get('end_date', default=None)

    # Get the report data frame
    reporter = ImpactReporter()
    revenue_analysis_df = reporter.get_revenue_analysis_report(company_id, cooling_unit_ids,
                                                              start_date, end_date)

    # Create and return the excel
    excel_writer = BytesIO()
    revenue_analysis_df.to_excel(excel_writer, sheet_name='Sheet1', index=False)
    excel_writer.seek(0)

    filename = f'revenue_analysis_comp_id_{company_id}_date_{time.strftime("%y-%m-%d")}.xlsx'
    response_content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response = Response(excel_writer.read(), content_type=response_content_type)
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'

    return response

if __name__ == '__main__':
    app.run(debug=True)
