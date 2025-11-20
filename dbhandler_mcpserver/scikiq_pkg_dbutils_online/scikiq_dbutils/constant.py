class DayWeekYear:
    SUNDAY_WKY_YYYY='SUNDAY WKy(yyyy)'
    SUNDAY_WKY_YY='SUNDAY WKy(yy)'
    SUNDAY_WK_N_OF_Y_YY='SUNDAY WK n of y(yy)'
    SUNDAY_WEEK_N_OF_Y_YY = 'SUNDAY Week n of y(yy)'
    SUNDAY_WEEK_N_OF_MY_YY = 'SUNDAY Week n of My(yy)'
    MONDAY_WKY_YYYY = 'MONDAY WKy(yyyy)'
    MONDAY_WKY_YY = 'MONDAY WKy(yy)'
    MONDAY_WEEK_N_OF_MY_YY = 'MONDAY Week n of My(yy)'
    MONDAY_WK_N_OF_Y_YY= 'MONDAY WK n of y(yy)'
    MONDAY_WEEK_N_OF_Y_YY = 'MONDAY Week n of y(yy)'
    

class QuaterYear:
    CY_QUARTERNTH_YYYY = 'CY Quarternth-yyyy'
    CY_QNTH_YYYY ='CY Qnth-yyyy'
    CY_QNTH_YY = 'CY Qnth-yy'
    FY_QUARTERNTH_YYYY = 'FY Quarternth-yyyy'
    FY_QNTH_YYYY = 'FY Qnth-yyyy'
    FY_QNTH_YY = 'FY Qnth-yy'

class DayMonthYear:
    D_M_Y='d/m/y'
    D_MM_Y ='d/MM/Y'
    D_M_Y_SHORT ='d/M/Y'


expressionsDict = {
    'changeToLowerCase':"lower({a})",
    'changeToCapitalizeCase':"initcap({a})",
    'changeToUpperCase': "upper({a})",
    'calculateLength': "length({a})",
    'aPlusB':"{a} + {b}",
    'aMinusB':"{a} - {b}",
    'aMultiplyB':"{a} * {b}",
    'aDivideB':"{a} / {b}",
    'aPlusBPlusC':"{a} + {b} + {c}",
    'column1Column2':"{a} {op1} {b}",
    'column1Column2Column3':"{a} {op1} {b} {op2} {c}",
    'remainderOfADivideB': "{a} / {b}"
}

week_year_value = {
    'SUNDAY_WKY_YYYY' : "concat(concat(concat(concat('WK',week(date(to_date(columnName::varchar,'yyyy-mm-dd')))),'('),year(to_date(columnName::varchar,'yyyy-mm-dd'))),')')",
    'SUNDAY_WKY_YY' : "concat(concat(concat(concat('WK',week(date(to_date(columnName::varchar,'yyyy-mm-dd')))),'('),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'YY')),')')",
    'SUNDAY_WK_N_OF_Y_YY' : "concat(concat(concat('WK ',week(date(to_date(columnName::varchar,'yyyy-mm-dd')))),' of '),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'YYYY'))",
    'SUNDAY_WEEK_N_OF_Y_YY' : "concat(concat(concat('WeeK ',week(date(to_date(columnName::varchar,'yyyy-mm-dd')))),' of '),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'YYYY'))",
    'SUNDAY_WEEK_N_OF_MY_YY' : "concat(concat(concat('WeeK ',week(date(to_date(columnName::varchar,'yyyy-mm-dd')))),' of '),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'Mon-YYYY'))"

}
    
dating_format = {
    'yyyy':"to_char(columnName,'yyyy') AS year ", 
    'y-mm' : "To_Char(columnName ,'YY-Mon') ",
    'YY-mm-DD': "To_Char(columnName,'YYYY-MM-Day') ",
    'YY-mm-D': "To_Char(columnName,'YYYY-MM-Dy') ",
    'y-m-DD': "To_Char(columnName,'YY-MM-day') ",
    'yy-MM-DD': "To_Char(columnName,'YYYY-Month-Day') ",
    'yy-MM-D': "To_Char(columnName,'YYYY-Month-Dy') ",
    'yy-M-DD': "To_Char(columnName,'YYYY-Mon-Day') ",
    'y-M-DD':"To_Char(columnName,'YY-Mon-Day') ",
    'D_M_Y': "To_Char(columnName,'dd/mm/yyyy') ",
    'D_MM_Y': "To_Char(columnName,'dd/month/yyyy') ",
    'D_M_Y_SHORT': "To_Char(columnName,'dd/mm/yy') ",
    'M-Y' : "To_Char(columnName,'month-yyyy') ",
    'm-Y' : "To_Char(columnName,'mm-yyyy') ",
    'M-y': "To_Char(columnName,'month-yy') ",
    'Y-m': "To_Char(columnName,'yyyy-mm') ",
    'Y-M': "To_Char(columnName,'yyyy-month') ",
    'w-d': "to_char( columnName,'D') ",
    'weekmonth': "to_char(columnName ,'W') ",
    'yy-mm-dd': "to_char(columnName,'yyyy-mm-dd')"
}

date_time_format = {
    'dateAPlusBHours': "columnName + INTERVAL '1' hour",
    'dateAPlusBSeconds': "columnName + INTERVAL '1' second",
    'dateAPlusBMinutes': "columnName + INTERVAL '1' minute",
    'dateAPlusBDays': "columnName + INTERVAL '1' day",
    'dateAPlusBMonths': "columnName + INTERVAL '1' month"
}

date_replace_format = {
    'yy-MM-dd' : "REPLACE(to_char(columnName,'YY-Month-dd'),' ','')",                                                                                                                                 
    'yy-M-dd'  : "replace((to_char(columnName,'yyyy-Mon-dd')),' ','')",                                                                   
    'y-M-dd'   : "replace((to_char(columnName,'yy-Mon-dd')),' ','')",                                                                
    'yy-M'     : "replace((to_char(columnName,'yyyy-Mon')),' ','')",                                                                     
    'y-M'      : "replace((to_char(columnName,'yy-Mon')),' ','')",                                                                      
    'yy-mm-DD' : "replace((to_char(columnName,'yyyy-MM-Day')),' ','')",                                                                   
    'yy-mm-D'  : "replace((to_char(columnName,'yyyy-MM-Dy')),' ','')" 
}