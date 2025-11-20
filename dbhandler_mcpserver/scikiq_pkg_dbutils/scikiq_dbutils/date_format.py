from scikiq_dbutils.constant import DayWeekYear,QuaterYear,expressionsDict,DayMonthYear,week_year_value,dating_format,date_time_format,date_replace_format

class GetDBDateFormat:
    format_string_dict={}
    mysql_format_dict = {}
    mssql_format_dict = {}
    vertica_format_dict = {}
    oracle_format_dict = {}
    teradata_format_dict = {}
    db2_format_dict = {}
    postgres_format_dict = {}

    # MYSQL formats
    mysql_format_dict[DayWeekYear.SUNDAY_WKY_YYYY]          = 'concat("WK",week(columnName),"(",year(columnName),")")'                                               #WK14(1970)
    mysql_format_dict[DayWeekYear.SUNDAY_WKY_YY]            = "concat('WK',week(columnName),'(',date_format(columnName,'%y'),')')"                                   #WK14(70)
    mysql_format_dict[DayWeekYear.SUNDAY_WK_N_OF_Y_YY]      = 'concat("WK ",week(columnName)," of ",date_format(columnName,"%Y"))'                                   #WK 14 of 1970
    mysql_format_dict[DayWeekYear.SUNDAY_WEEK_N_OF_Y_YY]    = 'concat("Week ",week(columnName)," of ",date_format(columnName,"%Y"))'                                 #Week 14 of 1970
    mysql_format_dict[DayWeekYear.SUNDAY_WEEK_N_OF_MY_YY]   = 'concat("Week ",week(columnName)," of ",date_format(columnName,"%M-%Y"))'                              #Week 1 of Jan-1970
    mysql_format_dict[DayWeekYear.MONDAY_WKY_YYYY]          = 'concat("WK",week(columnName,1),"(",year(columnName),")")'                                             #WK14(1970)
    mysql_format_dict[DayWeekYear.MONDAY_WKY_YY]            = 'concat("WK",week(columnName,1),"(",year(columnName),")")'                                             #WK14(70)
    mysql_format_dict[DayWeekYear.MONDAY_WEEK_N_OF_MY_YY]   = 'concat("Week ",week(columnName,1)," of ",date_format(columnName,"%M-%Y"))'                            #Week 1 of Jan-1970
    mysql_format_dict[QuaterYear.CY_QNTH_YY]                = 'concat("Quarter",quarter(columnName),"-",date_format(columnName,"%Y"))'                               #Quarter1-1970
    mysql_format_dict[QuaterYear.CY_QNTH_YYYY]              = "concat('Q',quarter(columnName),'-',date_format(columnName,'%Y'))"                                     #Q1-1970
    mysql_format_dict[QuaterYear.CY_QNTH_YY]                = "concat('Q',quarter(columnName),'-',date_format(columnName,'%y'))"                                     #Q1-70
    mysql_format_dict[QuaterYear.FY_QUARTERNTH_YYYY]        = 'case when month(columnName) between 4 and 6 then concat(concat("Quarter1","-"),year( columnName))\
                                                 when month( columnName) between 7 and 9 then concat(concat("Quarter2","-"),year(columnName))\
                                                 when month( columnName) between 10 and 12  then concat(concat("Quarter3","-"),year( columnName))\
                                                 else  concat(concat("Quarter4","-"),year(columnName)) end '                              #Quarter1-1970
    mysql_format_dict[QuaterYear.FY_QNTH_YYYY]              = 'case when month(columnName) between 4 and 6 then concat(concat("Q1","-"),year( columnName))\
                                                 when month( columnName) between 7 and 9 then concat(concat("Q2","-"),year(columnName))\
                                                 when month( columnName) between 10 and 12  then concat(concat("Q3","-"),year( columnName))\
                                                 else  concat(concat("Q4","-"),year(columnName)) end '                                    #Q1-1970
    mysql_format_dict[QuaterYear.FY_QNTH_YY]                = 'case when month(columnName) between 4 and 6 then concat(concat("Q1","-"),date_format(columnName,"%y"))\
												 when month( columnName) between 7 and 9 then concat(concat("Q2","-"),date_format(columnName,"%y"))\
												 when month( columnName) between 10 and 12  then concat(concat("Q3","-"),date_format(columnName,"%y"))\
                                                 else  concat(concat("Q4","-"),date_format(columnName,"%y")) end '                         #Q1-70
    mysql_format_dict['yyyy']                   = 'year(columnName)'                                                                                   #1970
    mysql_format_dict['FY-yyyy']                = "concat(year(columnName),'-',year(columnName)+1)"                                                       #1969-1970
    mysql_format_dict['yy-MM-DD']               = "date_format(columnName,'%Y-%M-%W')"                                                                 #1947-March-Friday
    mysql_format_dict['yy-MM-D']                = "date_format(columnName,'%Y-%M-%a')"                                                                 #1947-March-Fri
    mysql_format_dict['yy-M-DD']                = "date_format(columnName,'%Y-%b-%W')"                                                                 #1947-Mar-Friday
    mysql_format_dict['y-M-DD']                 = "date_format(columnName,'%y-%b-%W')"                                                                 #47-Mar-Friday
    mysql_format_dict[DayMonthYear.D_M_Y]       = "date_format(columnName,'%d/%m/%Y')"                                                                 #24/10/2020
    mysql_format_dict[DayMonthYear.D_MM_Y]      = "date_format(columnName,'%d/%M/%Y')"                                                                   #24/October/2020
    mysql_format_dict[DayMonthYear.D_M_Y_SHORT] = "date_format(columnName,'%d/%m/%y')"                                                                   #24/10/20
    mysql_format_dict['M-Y']                    = "date_format(columnName,'%M-%Y')"                                                                    #October-2020
    mysql_format_dict['m-Y']                    = "date_format(columnName,'%m-%Y')"                                                                    #10-2020
    mysql_format_dict['M-y']                    = "date_format(columnName,'%M-%y')"                                                                    #October-20
    mysql_format_dict['Y-m']                    = "date_format(columnName,'%Y-%m')"                                                                    #2020-10
    mysql_format_dict['Y-M']                    = "date_format(columnName,'%Y-%M'))"                                                                   #2020-October
    mysql_format_dict['w-d']                    = "dayofweek(columnName)"                                                                              #7
    mysql_format_dict['weekstartdate']          = "date_sub(columnName,interval dayofweek(columnName)-2 day)"                                             #2020-10-19
    mysql_format_dict['weekmonth']              = "WEEK(columnName) - WEEK(columnName - INTERVAL DAY(columnName)-1 DAY) + 1"                                 #4
    mysql_format_dict['changeToLowerCase']      = expressionsDict.get('changeToLowerCase')
    mysql_format_dict['changeToCapitalizeCase'] = expressionsDict.get('changeToCapitalizeCase')
    mysql_format_dict['calculateLength']        = "length({a})"
    mysql_format_dict['changeToUpperCase']      = expressionsDict.get('changeToUpperCase')
    mysql_format_dict['aPlusB']                 = expressionsDict.get('aPlusB')
    mysql_format_dict['aMinusB']                = expressionsDict.get('aMinusB')
    mysql_format_dict['aMultiplyB']             = expressionsDict.get('aMultiplyB')
    mysql_format_dict['aDivideB']               = expressionsDict.get('aDivideB')
    mysql_format_dict['aPlusBPlusC']            = expressionsDict.get('aPlusBPlusC')
    mysql_format_dict['column1Column2']         = expressionsDict.get('column1Column2')
    mysql_format_dict['column1Column2Column3']  = expressionsDict.get('column1Column2Column3')
    mysql_format_dict['customExpression']       = ""
    mysql_format_dict['remainderOfADivideB']    = expressionsDict.get('remainderOfADivideB')
    mysql_format_dict['dateAPlusBHours']        = "date_add(columnName,interval 1 hour)"
    mysql_format_dict['dateAPlusBSeconds']      = "date_add(now(),interval 1 second)"
    mysql_format_dict['dateAPlusBMinutes']      = "date_add(now(),interval 1 minute)"
    mysql_format_dict['dateAPlusBDays']         = "date_add(now(),interval 1 day)"
    mysql_format_dict['dateAPlusBMonths']       = "date_add(now(),interval 1 month)"
    mysql_format_dict['dateAMinusBHours']       = "date_add(now(),interval -1 hour)"
    mysql_format_dict['dateAMinusBSeconds']     = "date_add(now(),interval -1 second)"
    mysql_format_dict['dateAMinusBMinutes']     = "date_add(now(),interval -1 minute)"
    mysql_format_dict['dateAMinusBDays']        = "date_add(now(),interval -1 day)"
    mysql_format_dict['dateAMinusBMonths']      = "date_add(now(),interval -1 month)"
    mysql_format_dict['compareAequalB']         = "{a} = {b}"
    mysql_format_dict['yy-mm-dd']               = "date_format(columnName,'%Y-%m-%d')"#1947-08-01
    mysql_format_dict['yy-mm-d']                = "date_format(columnName,'%Y-%m-%e')"#1947-08-1
    mysql_format_dict['yy-m-dd']                = "date_format(columnName,'%Y-%c-%d')"                                                                                       #1947-8-01
    mysql_format_dict['y-m-dd']                 = "date_format(columnName,'%y-%c-%d')"                                                                                       #47-8-01
    mysql_format_dict['yy-mm']                  = "date_format(columnName,'%Y-%m')"                                                                                          #1947-08
    mysql_format_dict['yy-m']                   = "date_format(columnName,'%Y-%c')"                                                                                          #1947-8
    mysql_format_dict['y-m']                    = "date_format(columnName,'%y-%m')"                                                                                          #47-8
    mysql_format_dict['yy-MM-dd']               = "date_format(columnName,'%Y-%M-%d')"                                                                                       #1947-March-01
    mysql_format_dict['yy-MM-d']                = "date_format(columnName,'%Y-%M-%e')"                                                                                       #1947-March-1
    mysql_format_dict['yy-M-dd']                = "date_format(columnName,'%Y-%b-%d')"                                                                                       #1947-Mar-01
    mysql_format_dict['y-M-dd']                 = "date_format(columnName,'%y-%b-%d')"                                                                                       #47-Mar-01
    mysql_format_dict['yy-M']                   = "date_format(columnName,'%Y-%b')"                                                                                          #1947-Mar
    mysql_format_dict['y-M']                    = "date_format(columnName,'%y-%b')"                                                                                          #47-Mar
    mysql_format_dict['yy-mm-DD']               = "date_format(columnName,'%Y-%m-%W')"                                                                                       #1947-08-Friday
    mysql_format_dict['yy-mm-D']                = "date_format(columnName,'%Y-%m-%a')"                                                                                       #1947-08-Fri
    mysql_format_dict['yy-m-DD']                = "date_format(columnName,'%Y-%c-%a')"
    mysql_format_dict['yy-mm-dd hh:mm:ss']      = "date_format(columnName,'%Y-%m-%d %h:%i:%s')"                                                                              #1947-8-Fri


	# MS SQL Formats
    mssql_format_dict[DayWeekYear.SUNDAY_WKY_YYYY]       = "concat('WK',DATEPART(week,convert(varchar(11),columnName,121)),'(',year(columnName),')')"            #WK14(1970)
    mssql_format_dict[DayWeekYear.SUNDAY_WKY_YY]         = "concat('WK',DATEPART(week,convert(varchar(11),columnName,121)),'(',right(convert(varchar(10),year(columnName)),2),')')"    #WK14(70)
    mssql_format_dict[DayWeekYear.SUNDAY_WK_N_OF_Y_YY]   = "concat('WK ',DATEPART(week,convert(varchar(11),columnName,121)),' of ',year(columnName))"                                  #WK 14 of 1970
    mssql_format_dict[DayWeekYear.SUNDAY_WEEK_N_OF_Y_YY] = "concat('Week ',DATEPART(week,convert(varchar(11),columnName,121)),' of ',year(columnName))"                                #Week 14 of 1970
    mssql_format_dict[DayWeekYear.SUNDAY_WEEK_N_OF_MY_YY]= "concat('Week ',DATEPART(wk,convert(varchar(11),columnName,121)),' of ',format(columnName,'MMM'),'-',Year(columnName))"        #Week 1 of Jan-1970
    mssql_format_dict[QuaterYear.CY_QNTH_YY]     = "concat('Quarter',datepart(q,columnName),'-',Year(columnName))"                                                             #Quarter1-1970
    mssql_format_dict[QuaterYear.CY_QNTH_YYYY]           = "concat('Q',datepart(q,columnName),'-',Year(columnName))"                                                                   #Q1-1970
    mssql_format_dict[QuaterYear.CY_QNTH_YY]             = "concat('Q',datepart(q,columnName),'-',right(convert(varchar(10),year(columnName)),2))"                                     #Q1-70
    mssql_format_dict[QuaterYear.FY_QUARTERNTH_YYYY]     = "case when month(columnName) between 4 and 6 then concat('Quarter1','-',year( columnName))\
                                                 when month( columnName) between 7 and 9 then concat('Quarter2','-',year(columnName))\
                                                 when month( columnName) between 10 and 12  then concat('Quarter3','-',year( columnName))\
                                                 else  concat('Quarter4','-',year(columnName)) end "                                                             #Quarter1-1970
    mssql_format_dict[QuaterYear.FY_QNTH_YYYY]           = "case when month(columnName) between 4 and 6 then concat('Q1','-',year( columnName))\
                                                 when month( columnName) between 7 and 9 then concat('Q2','-',year(columnName))\
                                                 when month( columnName) between 10 and 12  then concat('Q3','-',year( columnName))\
                                                 else  concat('Q4','-',year(columnName)) end "                                                                   #Q1-1970
    mssql_format_dict[QuaterYear.FY_QNTH_YY]             = "case when month(columnName) between 4 and 6 then concat('Quarter1','-',right(convert(varchar(10),year(columnName)),2))\
                                                 when month( columnName) between 7 and 9 then concat('Quarter2','-',right(convert(varchar(10),year(columnName)),2))\
                                                 when month( columnName) between 10 and 12  then concat('Quarter3','-',right(convert(varchar(10),year(columnName)),2))\
                                                 else  concat('Quarter4','-',right(convert(varchar(10),year(columnName)),2)) end "                               #Q1-70
    mssql_format_dict['yyyy']                   = "year(columnName)"                                                                                                         #1970
    mssql_format_dict['FY-yyyy']                = "case when month(getdate()) >= 4 then concat(year(getdate()),'-',year(getdate())+1)\
                                                 else concat(year(getdate())-1,'-',year(getdate())) end"                                                                #1969-1970
    mssql_format_dict['yy-MM-DD']               = "concat(year(columnName),'-',format(columnName,'MMMM'),'-',format(columnName,'dddd'))"                                           #1947-March-Friday
    mssql_format_dict['yy-MM-D']                = "concat(year(columnName),'-',format(columnName,'MMMM'),'-',format(columnName,'ddd'))"                                            #1947-March-Fri
    mssql_format_dict['yy-M-DD']                = "concat(year(columnName),'-',format(columnName,'MMM'),'-',format(columnName,'dddd'))"                                            #1947-Mar-Friday
    mssql_format_dict['y-M-DD']                 = "concat(right(convert(varchar(10),year(columnName)),2),'-',format(columnName,'MMM'),'-',format(columnName,'dddd'))"              #47-Mar-Friday
    mssql_format_dict[DayMonthYear.D_M_Y]                  = "CONVERT(VARCHAR(10), columnName,103)"                                                                                     #24/10/2020
    mssql_format_dict[DayMonthYear.D_MM_Y]                  = "concat(format(columnName,'dd'),'/',format(columnName,'MMMM'),'/',format(columnName,'yyyy'))"                                    #24/October/2020
    mssql_format_dict[DayMonthYear.D_M_Y_SHORT]                  = "CONVERT(VARCHAR(10), columnName,3))"                                                                                      #24/10/20
    mssql_format_dict['yy-mm-dd']               = "convert(varchar,columnName,23)"                                                                                           #1947-08-01
    mssql_format_dict['yy-mm-d']                = "FORMAT(columnName, 'yyyy-MM-dd')"                                                                                         #1947-08-1
    mssql_format_dict['yy-m-dd']                = "FORMAT(columnName, 'yyyy-M-dd')"                                                                                          #1947-8-01
    mssql_format_dict['y-m-dd']                 = "FORMAT(columnName, 'yy-M-dd')"                                                                                            #47-8-01
    mssql_format_dict['yy-mm']                  = "FORMAT(columnName, 'yyyy-MM')"                                                                                            #1947-08
    mssql_format_dict['yy-m']                   = "FORMAT(columnName, 'yyyy-M')"                                                                                             #1947-8
    mssql_format_dict['y-m']                    = "FORMAT(columnName, 'yy-M')"                                                                                               #47-8
    mssql_format_dict['yy-MM-dd']               = "FORMAT(columnName, 'yyyy-MMMM-dd')"                                                                                       #1947-March-01
    mssql_format_dict['yy-MM-d']                = "FORMAT(columnName, 'yyyy-MMMM-d')"                                                                                        #1947-March-1
    mssql_format_dict['yy-M-dd']                = "FORMAT(columnName, 'yyyy-MMM-dd')"                                                                                        #1947-Mar-01
    mssql_format_dict['y-M-dd']                 = "FORMAT(columnName, 'yy-MMM-dd')"                                                                                          #47-Mar-01
    mssql_format_dict['yy-M']                   = "FORMAT(columnName, 'yyyy-MMM')"                                                                                           #1947-Mar
    mssql_format_dict['y-M']                    = "FORMAT(columnName, 'yy-MMM')"                                                                                             #47-Mar
    mssql_format_dict['yy-mm-DD']               = "FORMAT(columnName, 'yyyy-MM-dddd')"                                                                                       #1947-08-Friday
    mssql_format_dict['yy-mm-D']                = "FORMAT(columnName, 'yyyy-MM-ddd')"                                                                                        #1947-08-Fri
    mssql_format_dict['yy-m-DD']                = "FORMAT(columnName, 'yyyy-M-ddd')"                                                                                         #1947-8-Fri
    mssql_format_dict['y-m-DD']                 = "FORMAT(columnName, 'yy-M-ddd')"                                                                                           #47-8-Friday
    mssql_format_dict['M-Y']                    = "concat(format(columnName,'MMMM'),'-',format(columnName,'yyyy'))"                                                             #October-2020
    mssql_format_dict['m-Y']                    = "concat(format(columnName,'MM'),'-',format(columnName,'yyyy'))"                                                               #10-2020
    mssql_format_dict['M-y']                    = "concat(format(columnName,'MMMM'),'-',format(columnName,'yy'))"                                                               #October-20
    mssql_format_dict['Y-m']                    = "concat(format(columnName,'yyyy'),'-',format(columnName,'MM'))"                                                               #2020-10
    mssql_format_dict['Y-M']                    = "concat(format(columnName,'yyyy'),'-',format(columnName,'MMMM'))"                                                             #2020-October
    mssql_format_dict['w-d']                    = "DATEPART(dw,columnName)"                                                                                                  #7
    mssql_format_dict['weekstartdate']          = "DATEADD(DAY,-DATEPART(dw,columnName)+2,CAST(columnName AS date)) "                                                           #2020-10-19
    mssql_format_dict['weekmonth']              = "DATEPART(WEEK, columnName)- DATEPART(WEEK, DATEADD(MM, DATEDIFF(MM,0,columnName), 0))+ 1"                                    #4
    mssql_format_dict['changeToLowerCase']      = expressionsDict.get('changeToLowerCase')
    mssql_format_dict['changeToCapitalizeCase'] = ""
    mssql_format_dict['calculateLength']        = "len({a})"
    mssql_format_dict['changeToUpperCase']      = expressionsDict.get('changeToUpperCase')
    mssql_format_dict['aPlusB']                 = expressionsDict.get('aPlusB')
    mssql_format_dict['aMinusB']                = expressionsDict.get('aMinusB')
    mssql_format_dict['aMultiplyB']             = expressionsDict.get('aMultiplyB')
    mssql_format_dict['aDivideB']               = expressionsDict.get('aDivideB')
    mssql_format_dict['aPlusBPlusC']            = expressionsDict.get('aPlusBPlusC')
    mssql_format_dict['column1Column2']         = expressionsDict.get('column1Column2')
    mssql_format_dict['column1Column2Column3']  = expressionsDict.get('column1Column2Column3')
    mssql_format_dict['customExpression']       = ""
    mssql_format_dict['remainderOfADivideB']    = expressionsDict.get('remainderOfADivideB')
    mssql_format_dict['dateAPlusBHours']        = "dateadd(hour,1,columnName)"
    mssql_format_dict['dateAPlusBSeconds']      = "dateadd(second,1,columnName)"
    mssql_format_dict['dateAPlusBMinutes']      = "dateadd(minute,1,columnName)"
    mssql_format_dict['dateAPlusBDays']         = "dateadd(day,1,columnName)"
    mssql_format_dict['dateAPlusBMonths']       = "dateadd(month,1,columnName)"
    mssql_format_dict['dateAMinusBHours']       = "dateadd(hour,-1,columnName)"
    mssql_format_dict['dateAMinusBSeconds']     = "dateadd(second,-1,columnName)"
    mssql_format_dict['dateAMinusBMinutes']     = "dateadd(minute,-1,columnName)"
    mssql_format_dict['dateAMinusBDays']        = "dateadd(day,-1,columnName)"
    mssql_format_dict['dateAMinusBMonths']      = "dateadd(month,-1,columnName)"
    mssql_format_dict['compareAequalB']         = ""
    mssql_format_dict['yy-mm-dd hh:mm:ss']      = "convert(varchar,columnName,20)"


	# Vertica Sql Formats
    vertica_format_dict[DayWeekYear.SUNDAY_WKY_YYYY]       = week_year_value.get('SUNDAY_WKY_YYYY')                     #WK14(1970)
    vertica_format_dict[DayWeekYear.SUNDAY_WKY_YY]         = week_year_value.get('SUNDAY_WKY_YY')         #WK14(70)
    vertica_format_dict[DayWeekYear.SUNDAY_WK_N_OF_Y_YY]   = week_year_value.get('SUNDAY_WK_N_OF_Y_YY')              #WK 14 of 1970
    vertica_format_dict[DayWeekYear.SUNDAY_WEEK_N_OF_Y_YY] = week_year_value.get('SUNDAY_WEEK_N_OF_Y_YY')            #Week 14 of 1970
    vertica_format_dict[DayWeekYear.SUNDAY_WEEK_N_OF_MY_YY]= week_year_value.get('SUNDAY_WEEK_N_OF_MY_YY')       #Week 1 of Jan-1970
    vertica_format_dict[DayWeekYear.MONDAY_WKY_YYYY]       ="concat(concat(concat(concat('WK',week_iso(date(to_date(columnName::varchar,'yyyy-mm-dd')))),'('),year(to_date(columnName::varchar,'yyyy-mm-dd'))),')')"                   #WK14(1970)
    vertica_format_dict[DayWeekYear.MONDAY_WKY_YY]         ="concat(concat(concat(concat('WK',week_iso(date(to_date(columnName::varchar,'yyyy-mm-dd')))),'('),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'YY')),')')"     #WK14(70)
    vertica_format_dict[DayWeekYear.MONDAY_WK_N_OF_Y_YY]   ="concat(concat(concat('WK ',week_iso(date(to_date(columnName::varchar,'yyyy-mm-dd')))),' of '),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'YYYY'))"          #WK 14 of 1970
    vertica_format_dict[DayWeekYear.MONDAY_WEEK_N_OF_Y_YY] ="concat(concat(concat('WeeK ',week_iso(date(to_date(columnName::varchar,'yyyy-mm-dd')))),' of '),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'YYYY'))"        #Week 14 of 1970
    vertica_format_dict[DayWeekYear.MONDAY_WEEK_N_OF_MY_YY]="concat(concat(concat('WeeK ',week_iso(date(to_date(columnName::varchar,'yyyy-mm-dd')))),' of '),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'Mon-YYYY'))"    #Week 1 of Jan-1970
    vertica_format_dict['CY Quarter-yyyy']     ="concat(concat(concat('Quarter', quarter(to_date(columnName::varchar,'yyyy-mm-dd'))),'-'),year(to_date(columnName::varchar,'yyyy-mm-dd'))) "                     #Quarter1-1970
    vertica_format_dict['CY Q-yy']             ="concat(concat(concat('Q', quarter(to_date(columnName::varchar,'yyyy-mm-dd'))),'-'),year(to_date(columnName::varchar,'yyyy-mm-dd'))) "                           #Q1-1970
    vertica_format_dict['CY Q-yyyy']             ="concat(concat(concat('Q', quarter(to_date(columnName::varchar,'yyyy-mm-dd'))),'-'),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'YY')) "              #Q1-70
    vertica_format_dict['FY Quarter-yyyy']     ="case when month(to_date(columnName::varchar,'yyyy-mm-dd')) between 4 and 6 then concat(concat('Quarter1','-'),year( to_date(columnName::varchar,'yyyy-mm-dd')))\
                                                  when month( to_date(columnName::varchar,'yyyy-mm-dd')) between 7 and 9 then concat(concat('Quarter2','-'),year(to_date(columnName::varchar,'yyyy-mm-dd')))\
                                                  when month( to_date(columnName::varchar,'yyyy-mm-dd')) between 10 and 12  then concat(concat('Quarter3','-'),year( to_date(columnName::varchar,'yyyy-mm-dd')))\
                                                  else  concat(concat('Quarter4','-'),year(to_date(columnName::varchar,'yyyy-mm-dd'))) end "                                    #Quarter1-1970
    vertica_format_dict['FY Q-yyyy']             ="case when month(to_date(columnName::varchar,'yyyy-mm-dd')) between 4 and 6 then concat(concat('Q1','-'),year(getdate()))\
                                                  when month( to_date(columnName::varchar,'yyyy-mm-dd')) between 7 and 9 then concat(concat('Q2','-'),year(getdate()))\
                                                  when month( to_date(columnName::varchar,'yyyy-mm-dd')) between 10 and 12  then concat(concat('Q3','-'),year(getdate()))\
                                                  else  concat(concat('Q4','-'),year(getdate())) end "                                        #Q1-1970
    vertica_format_dict['FY Q-yy']             ="case when month(to_date(columnName::varchar,'yyyy-mm-dd')) between 4 and 6 then concat(concat('Q1','-'),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'YY'))\
                                                  when month( to_date(columnName::varchar,'yyyy-mm-dd')) between 7 and 9 then concat(concat('Q2','-'),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'YY'))\
                                                  when month( to_date(columnName::varchar,'yyyy-mm-dd')) between 10 and 12  then concat(concat('Q3','-'),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'YY'))\
                                                  else  concat(concat('Q4','-'),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'YY')) end "                            #Q1-70
    vertica_format_dict['yyyy']                   ="year(to_date(columnName::varchar,'yyyy-mm-dd'))"                                                                                        #1970
    vertica_format_dict['FY-yyyy']                ="case when month(getdate()) >=4 then concat(concat(year(to_date(columnName::varchar,'yyyy-mm-dd')),'-'),year(to_date(columnName::varchar,'yyyy-mm-dd'))+1)\
                                                  else concat(concat(year(to_date(columnName::varchar,'yyyy-mm-dd'))-1,'-'),year(to_date(columnName::varchar,'yyyy-mm-dd'))) end"                                           #1969-1970
    vertica_format_dict['y-mm']                    ="To_Char(to_date(columnName::varchar,'yyyy-mm-dd'),'YY-Mon')"                                                                            #47-Mar
    vertica_format_dict['YY-mm-DD']               ="To_Char(to_date(columnName::varchar,'yyyy-mm-dd'),'YYYY-MM-Day')"                                                                       #1947-08-Friday
    vertica_format_dict['YY-mm-D']                ="To_Char(to_date(columnName::varchar,'yyyy-mm-dd'),'YYYY-MM-Dy')"                                                                        #1947-08-Fri
    vertica_format_dict['YY-m-DD']                ="To_Char(to_date(columnName::varchar,'yyyy-mm-dd'),'YYYY-MM-Day')"                                                                       #1947-8-Friday
    vertica_format_dict['y-m-DD']                 ="To_Char(to_date(columnName::varchar,'yyyy-mm-dd'),'YY-MM-day')"                                                                         #47-8-Friday
    vertica_format_dict['yy-MM-DD']               ="To_Char(to_date(columnName::varchar,'yyyy-mm-dd'),'YYYY-Month-Day')"                                                                    #1947-March-Friday
    vertica_format_dict['yy-MM-D']                ="To_Char(to_date(columnName::varchar,'yyyy-mm-dd'),'YYYY-Month-Dy')"                                                                     #1947-March-Fri
    vertica_format_dict['yy-M-DD']                ="To_Char(to_date(columnName::varchar,'yyyy-mm-dd'),'YYYY-Mon-Day')"                                                                      #1947-Mar-Friday
    vertica_format_dict['y-M-DD']                 ="To_Char(to_date(columnName::varchar,'yyyy-mm-dd'),'YY-Mon-Day')"                                                                        #47-Mar-Friday
    vertica_format_dict[DayMonthYear.D_M_Y]                  ="To_Char(to_date(columnName::varchar,'yyyy-mm-dd'),'dd/mm/yyyy')"                                                                        #24/10/2020
    vertica_format_dict[DayMonthYear.D_MM_Y]                  = "To_Char(to_date(columnName::varchar,'yyyy-mm-dd'),'dd/month/yyyy')"                                                                    #24/October/2020
    vertica_format_dict[DayMonthYear.D_M_Y_SHORT]                  = "To_Char(to_date(columnName::varchar,'yyyy-mm-dd'),'dd/mm/yy')"                                                                         #24/10/20
    vertica_format_dict['M-Y']                    = "To_Char(to_date(columnName::varchar,'yyyy-mm-dd'),'month-yyyy')"                                                                       #October-2020
    vertica_format_dict['m-Y']                    = "To_Char(to_date(columnName::varchar,'yyyy-mm-dd'),'mm-yyyy')"                                                                          #10-2020
    vertica_format_dict['M-y']                    = "To_Char(to_date(columnName::varchar,'yyyy-mm-dd'),'month-yy')"                                                                         #October-20
    vertica_format_dict['Y-m']                    = "To_Char(to_date(columnName::varchar,'yyyy-mm-dd'),'yyyy-mm')"                                                                          #2020-10
    vertica_format_dict['Y-M']                    = "To_Char(to_date(columnName::varchar,'yyyy-mm-dd'),'yyyy-month')"                                                                       #2020-October
    vertica_format_dict['w-d']                    = "DAYOFWEEK(to_date(columnName::varchar,'yyyy-mm-dd'))"                                                                                  #7
    vertica_format_dict['weekstartdate']          = "date(date_trunc('week', to_date(columnName::varchar,'yyyy-mm-dd')))"                                                                   #2020-10-19
    vertica_format_dict['weekmonth']              = "(week(date(to_date(columnName::varchar,'yyyy-mm-dd'))) - week(date(to_date(columnName::varchar,'yyyy-mm-dd') - dayofmonth(to_date(columnName::varchar,'yyyy-mm-dd'))+1)))+1"                               #4
    #a,b and c here column name, "op" means operator
    vertica_format_dict['changeToLowerCase']       = expressionsDict.get('changeToLowerCase')
    vertica_format_dict['changeToCapitalizeCase']  = expressionsDict.get('changeToCapitalizeCase')
    vertica_format_dict['calculateLength']         = expressionsDict.get('calculateLength')
    vertica_format_dict['changeToUpperCase']       = expressionsDict.get('changeToUpperCase')
    vertica_format_dict['aPlusB']                  = expressionsDict.get('aPlusB')
    vertica_format_dict['aMinusB']                 = expressionsDict.get('aMinusB')
    vertica_format_dict['aMultiplyB']              = expressionsDict.get('aMultiplyB')
    vertica_format_dict['aDivideB']                = expressionsDict.get('aDivideB')
    vertica_format_dict['aPlusBPlusC']             = expressionsDict.get('aPlusBPlusC')
    vertica_format_dict['column1Column2']          =  expressionsDict.get('column1Column2')
    vertica_format_dict['column1Column2Column3']   = expressionsDict.get('column1Column2Column3')
    vertica_format_dict['customExpression']        = ""
    vertica_format_dict['remainderOfADivideB']     = expressionsDict.get('remainderOfADivideB')
    vertica_format_dict['dateAPlusBHours']         = "TIMESTAMPADD(hour,1,now())"
    vertica_format_dict['dateAPlusBSeconds']       = "TIMESTAMPADD(second,1,now())"
    vertica_format_dict['dateAPlusBMinutes']       = "TIMESTAMPADD(minute,1,now())"
    vertica_format_dict['dateAPlusBDays']          = "TIMESTAMPADD(day,1,now())"
    vertica_format_dict['dateAPlusBMonths']        = "TIMESTAMPADD(month,1,now())"
    vertica_format_dict['dateAMinusBHours']        = "TIMESTAMPADD(hour,-1,now())"
    vertica_format_dict['dateAMinusBSeconds']      = "TIMESTAMPADD(second,-1,now())"
    vertica_format_dict['dateAMinusBMinutes']      = "TIMESTAMPADD(minute,-1,now())"
    vertica_format_dict['dateAMinusBDays']         = "TIMESTAMPADD(day,-1,now())"
    vertica_format_dict['dateAMinusBMonths']       = "TIMESTAMPADD(month,-1,now())"
    vertica_format_dict['compareAequalB']          = ""
    vertica_format_dict['yy-mm-dd']               = "to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'yyyy-mm-dd')"                                                                   #1947-08-01
    vertica_format_dict['yy-mm-d']                = "to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'yyyy-mm-FMDD')"                                                                                      #1947-08-1
    vertica_format_dict['yy-m-dd']                = "concat(concat(concat(concat(year(to_date(columnName::varchar,'yyyy-mm-dd')),'-'),month(to_date(columnName::varchar,'yyyy-mm-dd'))),'-'),to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'DD'))"                           #1947-8-01
    vertica_format_dict['y-m-dd']                 = "concat(concat(concat(concat(to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'yy'),'-'),month(to_date(columnName::varchar,'yyyy-mm-dd'))),'-'),to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'DD'))"                   #47-8-01
    vertica_format_dict['yy-mm']                  = "to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'yyyy-mm')"                                                                                           #1947-08
    vertica_format_dict['yy-m']                   = "concat(concat(concat(year(to_date(columnName::varchar,'yyyy-mm-dd')),'-'),month(to_date(columnName::varchar,'yyyy-mm-dd')))"                                                              #1947-8
    vertica_format_dict['y-m']                    = "concat(concat(to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'yy'),'-'),month(to_date(columnName::varchar,'yyyy-mm-dd')))"                                                             #47-8
    vertica_format_dict['yy-MM-dd']               = "replace((to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'yyyy-Month-dd')),' ','')"                                                                                     #1947-March-01
    vertica_format_dict['yy-MM-d']                = "replace((to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'yyyy-Month-FMdd')),' ','')"                                                                 #1947-March-1
    vertica_format_dict['yy-M-dd']                = "replace((to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'yyyy-Mon-dd')),' ','')"                                                                     #1947-Mar-01
    vertica_format_dict['y-M-dd']                 = "replace((to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'yy-Mon-dd')),' ','')"                                                                       #47-Mar-01
    vertica_format_dict['yy-M']                   = "replace((to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'yyyy-Mon')),' ','')"                                                                        #1947-Mar
    vertica_format_dict['y-M']                    = "replace((to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'yy-Mon')),' ','')"                                                                          #47-Mar
    vertica_format_dict['yy-mm-DD']               = "replace((to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'yyyy-MM-Day')),' ','')"                                                                     #1947-08-Friday
    vertica_format_dict['yy-mm-D']                = "replace((to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'yyyy-MM-Dy')),' ','')"                                                                      #1947-08-Fri
    vertica_format_dict['yy-m-DD']                = "concat(concat(concat(concat(to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'yyyy'),'-'),month(to_date(columnName::varchar,'yyyy-mm-dd'))),'-'),to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'Dy'))"                 #1947-8-Fri

    #01-1990
    vertica_format_dict['mm-yyyy']                  = "to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'MM-YYYY')"
    #1-1990
    vertica_format_dict['m-yyyy']                  = "concat(concat(month(to_date(columnName::varchar,'yyyy-mm-dd')),'-'),year(to_date(columnName::varchar,'yyyy-mm-dd')))"
    #Jan-1990
    vertica_format_dict['M-yyyy']                  = "concat(substring(to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'Month'),1,3),to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'-YYYY'))"
    #1990-Jan
    vertica_format_dict['yyyy-M']                  = "concat(to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'YYYY'),substring(to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'-Month'),1,4))"
    #January-1990
    vertica_format_dict['MM-yyyy']                  = "replace((concat(to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'Month'),to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'-YYYY'))),' ','')"
    #1990-January
    vertica_format_dict['yyyy-MM']                  = "concat(to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'YYYY'),to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'-Month'))"


    #01/1990
    vertica_format_dict['mm/yyyy']                  = "to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'MM/YYYY')"
    ##01-1990
    vertica_format_dict['m/yyyy']                   = "concat(concat(month(to_date(columnName::varchar,'yyyy-mm-dd')),'/'),year(to_date(columnName::varchar,'yyyy-mm-dd')))"
    #Jan-1990
    vertica_format_dict['M/yyyy']                   = "concat(substring(to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'Month'),1,3),to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'/YYYY'))"
    #1990-Jan
    vertica_format_dict['yyyy/M']                   = "concat(to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'YYYY'),substring(to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'/Month'),1,4))"
    #January-1990
    vertica_format_dict['MM/yyyy']                  = "replace(concat(to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'Month'),to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'/YYYY')),' ','')"
    #1990-January
    vertica_format_dict['yyyy/MM']                  = "concat(to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'YYYY'),to_char(to_date(columnName::varchar,'yyyy-mm-dd'),'/Month'))"

    vertica_format_dict['WKy(yyyy)']                =week_year_value.get('SUNDAY_WKY_YYYY')                       #WK14(1970)
    vertica_format_dict['WKy(yy)']                  =week_year_value.get('SUNDAY_WKY_YY')         #WK14(70)
    vertica_format_dict['WK n of y(yy)']            =week_year_value.get('SUNDAY_WK_N_OF_Y_YY')              #WK 14 of 1970
    vertica_format_dict['Week n of y(yy)']          ="concat(concat(concat('WeeK ',week(date(to_date(columnName::varchar,'yyyy-mm-dd')))),' of '),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'YYYY'))"            #Week 14 of 1970
    vertica_format_dict['Week n of My(yy)']         ="concat(concat(concat('WeeK ',week(date(to_date(columnName::varchar,'yyyy-mm-dd')))),' of '),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'Mon-YYYY'))"        #Week 1 of Jan-1970

    vertica_format_dict['sunday WKy(yyyy)']       =week_year_value.get('SUNDAY_WKY_YYYY')                       #WK14(1970)
    vertica_format_dict['sunday WKy(yy)']         =week_year_value.get('SUNDAY_WKY_YY')         #WK14(70)
    vertica_format_dict['sunday WK of y(yy)']   =week_year_value.get('SUNDAY_WK_N_OF_Y_YY')              #WK 14 of 1970
    vertica_format_dict['sunday Week of y(yy)'] ="concat(concat(concat('WeeK ',week(date(to_date(columnName::varchar,'yyyy-mm-dd')))),' of '),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'YYYY'))"            #Week 14 of 1970
    vertica_format_dict['sunday Week of MM-yyyy']="concat(concat(concat('WeeK ',week(date(to_date(columnName::varchar,'yyyy-mm-dd')))),' of '),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'Mon-YYYY'))"        #Week 1 of Jan-1970

    vertica_format_dict['monday WKy(yyyy)']       ="concat(concat(concat(concat('WK',week_iso(date(to_date(columnName::varchar,'yyyy-mm-dd')))),'('),year(to_date(columnName::varchar,'yyyy-mm-dd'))),')')"                   #WK14(1970)
    vertica_format_dict['monday WKy(yy)']         ="concat(concat(concat(concat('WK',week_iso(date(to_date(columnName::varchar,'yyyy-mm-dd')))),'('),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'YY')),')')"     #WK14(70)
    vertica_format_dict['monday WK of y(yy)']   ="concat(concat(concat('WK ',week_iso(date(to_date(columnName::varchar,'yyyy-mm-dd')))),' of '),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'YYYY'))"          #WK 14 of 1970
    vertica_format_dict['monday Week of y(yy)'] ="concat(concat(concat('WeeK ',week_iso(date(to_date(columnName::varchar,'yyyy-mm-dd')))),' of '),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'YYYY'))"        #Week 14 of 1970
    vertica_format_dict['monday Week of MM-yyyy']="concat(concat(concat('WeeK ',week_iso(date(to_date(columnName::varchar,'yyyy-mm-dd')))),' of '),to_char(date(to_date(columnName::varchar,'yyyy-mm-dd')),'Mon-YYYY'))"    #Week 1 of Jan-1970
    vertica_format_dict['yy-mm-dd hh:mm:ss'] = "to_char(to_timestamp(columnName::varchar,'yyyy-mm-dd hh24:MI:ss'),'yyyy-mm-dd hh24:MI:ss')"

    # Oracle  Formats
    # Note:- 1.Single digit date not available.
    #        2.Single digit month not available.
    oracle_format_dict[DayWeekYear.SUNDAY_WKY_YYYY]       ="concat(concat(concat(concat('WK',to_char(columnName,'ww')),'('),to_char(columnName,'yyyy')),')') "             #WK14(1970)
    oracle_format_dict[DayWeekYear.SUNDAY_WKY_YY]         ="concat(concat(concat(concat('WK',to_char(columnName,'ww')),'('),to_char(columnName,'yy')),')') "               #WK14(70)
    oracle_format_dict[DayWeekYear.SUNDAY_WK_N_OF_Y_YY]   ="concat(concat(concat('WK ',to_char(columnName,'ww')),' of '),to_char(columnName,'yyyy')) "                    #WK 14 of 1970
    oracle_format_dict[DayWeekYear.SUNDAY_WEEK_N_OF_Y_YY] ="concat(concat(concat('WeeK ',to_char(columnName,'ww')),' of '),to_char(columnName,'yyyy')) "                  #Week 14 of 1970
    oracle_format_dict[DayWeekYear.SUNDAY_WEEK_N_OF_MY_YY]="concat(concat(concat('WeeK ',to_char(columnName,'ww')),' of '),to_char(columnName,'Mon-YYYY')) "              #Week 1 of Jan-1970
    oracle_format_dict[DayWeekYear.MONDAY_WKY_YYYY]       ="concat(concat(concat(concat('WK',to_char(columnName,'IW')),'('),to_char(columnName,'yyyy')),')') "             #WK14(1970)
    oracle_format_dict[DayWeekYear.MONDAY_WKY_YY]         ="concat(concat(concat(concat('WK',to_char(columnName,'IW')),'('),to_char(columnName,'yy')),')') "               #WK14(70)
    oracle_format_dict[DayWeekYear.MONDAY_WK_N_OF_Y_YY]   ="concat(concat(concat('WeeK ',to_char(columnName,'Iw')),' of '),to_char(columnName,'yyyy')) "                  #WK 14 of 1970
    oracle_format_dict[DayWeekYear.MONDAY_WEEK_N_OF_Y_YY] ="concat(concat(concat('WeeK ',to_char(columnName,'IW')),' of '),to_char(columnName,'yyyy')) "                  #Week 14 of 1970
    oracle_format_dict[DayWeekYear.MONDAY_WEEK_N_OF_MY_YY]="concat(concat(concat('WeeK ',to_char(columnName,'IW')),' of '),to_char(columnName,'Mon-YYYY')) "              #Week 1 of Jan-1970
    oracle_format_dict[QuaterYear.CY_QNTH_YY]     ="concat(concat(concat('Quarter', to_char(columnName,'q')),'-'),to_char(columnName,'yyyy'))  "         #Quarter1-1970
    oracle_format_dict[QuaterYear.CY_QNTH_YYYY]             ="concat(concat(concat('Q', to_char(columnName,'q')),'-'),to_char(columnName,'yyyy'))  "               #Q1-1970
    oracle_format_dict[QuaterYear.CY_QNTH_YY]             ="concat(concat(concat('Q', to_char(columnName,'q')),'-'),to_char(columnName,'yy'))  "                 #Q1-70
    oracle_format_dict[QuaterYear.FY_QUARTERNTH_YYYY]     ="case when to_char(columnName,'mm') between 4 and 6 then concat(concat('Quarter1','-'),to_char(columnName,'yyyy'))\
                                                when to_char(columnName,'mm') between 7 and 9 then concat(concat('Quarter2','-'),to_char(columnName,'yyyy'))\
                                                when to_char(columnName,'mm') between 10 and 12  then concat(concat('Quarter3','-'),to_char(columnName,'yyyy'))\
                                                else  concat(concat('Quarter4','-'),to_char(columnName,'yyyy')) end  "                              #Quarter1-1970
    oracle_format_dict[QuaterYear.FY_QNTH_YYYY]             ="case when to_char(columnName,'mm') between 4 and 6 then concat(concat('Q1','-'),to_char(columnName,'yyyy'))\
                                                 when to_char(columnName,'mm') between 7 and 9 then concat(concat('Q2','-'),to_char(columnName,'yyyy'))\
                                                 when to_char(columnName,'mm') between 10 and 12  then concat(concat('Q3','-'),to_char(columnName,'yyyy'))\
                                                 else  concat(concat('Q4','-'),to_char(columnName,'yyyy')) end  "                                   #Q1-1970
    oracle_format_dict[QuaterYear.FY_QNTH_YY]             ="case when to_char(columnName,'mm') between 4 and 6 then concat(concat('Q1','-'),to_char(columnName,'yy'))\
                                                 when to_char(columnName,'mm') between 7 and 9 then concat(concat('Q2','-'),to_char(columnName,'yy'))\
                                                 when to_char(columnName,'mm') between 10 and 12  then concat(concat('Q3','-'),to_char(columnName,'yy'))\
                                                 else  concat(concat('Q4','-'),to_char(columnName,'yy')) end  "                                      #Q1-70
    oracle_format_dict['yyyy']                   = dating_format.get('yyyy')                                                                          #1970
    oracle_format_dict['FY-yyyy']                ="case when to_char(columnName,'mm') >=4 then concat(concat(to_char(columnName,'yyyy'),'-'),to_char(columnName,'yyyy')+1)\
                                                else concat(concat(to_char(columnName,'yyyy')-1,'-'),to_char(columnName,'yyyy')) END "                             #1969-1970
    oracle_format_dict['y-mm']                    =  dating_format.get('y-mm')                                                                             #47-Mar
    oracle_format_dict['YY-mm-DD']               =dating_format.get('YY-mm-DD')                                                                           #1947-08-Friday
    oracle_format_dict['YY-mm-D']                =dating_format.get('YY-mm-D')                                                                             #1947-08-Fri
    oracle_format_dict['YY-m-DD']                =dating_format.get('YY-mm-DD')                                                                            #1947-8-Friday
    oracle_format_dict['y-m-DD']                 =dating_format.get('y-m-DD')                                                                              #47-8-Friday
    oracle_format_dict['yy-MM-DD']               =dating_format.get('yy-MM-DD')                                                                    #1947-March-Friday
    oracle_format_dict['yy-MM-D']                =dating_format.get('yy-MM-D')                                                                     #1947-March-Fri
    oracle_format_dict['yy-M-DD']                =dating_format.get('yy-M-DD')                                                                      #1947-Mar-Friday
    oracle_format_dict['y-M-DD']                 =dating_format.get('y-M-DD')                                                                        #47-Mar-Friday
    oracle_format_dict[DayMonthYear.D_M_Y]                    =dating_format.get('D_M_Y')                                                                      #24/10/2020
    oracle_format_dict[DayMonthYear.D_MM_Y]                    = dating_format.get('D_MM_Y')                                                                  #24/October/2020
    oracle_format_dict[DayMonthYear.D_M_Y_SHORT]                    = dating_format.get('D_M_Y_SHORT')                                                                       #24/10/20
    oracle_format_dict['M-Y']                      = dating_format.get('M-Y')                                                                     #October-2020
    oracle_format_dict['m-Y']                      = dating_format.get('m-Y')                                                                        #10-2020
    oracle_format_dict['M-y']                      = dating_format.get('M-y')                                                                       #October-20
    oracle_format_dict['Y-m']                      = dating_format.get('Y-m')                                                                        #2020-10
    oracle_format_dict['Y-M']                      = dating_format.get('Y-M')                                                                     #2020-October
    oracle_format_dict['w-d']                      = dating_format.get('w-d')                                                                             #7
    oracle_format_dict['weekstartdate']            = "to_char(TRUNC(columnName, 'iw'),'yyyy-mm-dd') "                                                        #2020-10-19
    oracle_format_dict['weekmonth']                = dating_format.get('weekmonth')                                                                             #4
    #a,b and c here column name, "op" means operator
    oracle_format_dict['changeToLowerCase']       = expressionsDict.get('changeToLowerCase')
    oracle_format_dict['changeToCapitalizeCase']  = expressionsDict.get('changeToCapitalizeCase')
    oracle_format_dict['calculateLength']         = expressionsDict.get('calculateLength')
    oracle_format_dict['changeToUpperCase']       = expressionsDict.get('changeToUpperCase')
    oracle_format_dict['aPlusB']                  = expressionsDict.get('aPlusB')
    oracle_format_dict['aMinusB']                 = expressionsDict.get('aMinusB')
    oracle_format_dict['aMultiplyB']              = expressionsDict.get('aMultiplyB')
    oracle_format_dict['aDivideB']                = expressionsDict.get('aDivideB')
    oracle_format_dict['aPlusBPlusC']             = expressionsDict.get('aPlusBPlusC')
    oracle_format_dict['column1Column2']          =  expressionsDict.get('column1Column2')
    oracle_format_dict['column1Column2Column3']   = expressionsDict.get('column1Column2Column3')
    oracle_format_dict['customExpression']        = ""
    oracle_format_dict['remainderOfADivideB']     = expressionsDict.get('remainderOfADivideB')
    oracle_format_dict['dateAPlusBHours']         = date_time_format.get('dateAPlusBHours')
    oracle_format_dict['dateAPlusBSeconds']       = date_time_format.get('dateAPlusBSeconds')
    oracle_format_dict['dateAPlusBMinutes']       = date_time_format.get('dateAPlusBMinutes')
    oracle_format_dict['dateAPlusBDays']          = date_time_format.get('dateAPlusBDays')
    oracle_format_dict['dateAPlusBMonths']        = date_time_format.get('dateAPlusBMonths')
    oracle_format_dict['dateAMinusBHours']        = "columnName + INTERVAL '-1' hour"
    oracle_format_dict['dateAMinusBSeconds']      = "columnName + INTERVAL '-1' second"
    oracle_format_dict['dateAMinusBMinutes']      = "columnName + INTERVAL '-1' minute"
    oracle_format_dict['dateAMinusBDays']         = "columnName + INTERVAL '-1' day"
    oracle_format_dict['dateAMinusBMonths']       = "columnName + INTERVAL '-1' month"
    oracle_format_dict['compareAequalB']          = ""
    oracle_format_dict['yy-mm-dd']               = dating_format.get('yy-mm-dd')                                                                                        #1947-08-01
    oracle_format_dict['yy-mm-d']                = "to_char(columnName,'yyyy-mm-FMDD')"                                                                                      #1947-08-1
    oracle_format_dict['yy-m-dd']                = "to_char(columnName,'YYYY-fmMM-fmdd')"                                                                                    #1947-8-01
    oracle_format_dict['y-m-dd']                 = "to_char(columnName,'YY-fmMM-fmdd')"                                                                                      #47-8-01
    oracle_format_dict['yy-mm']                  = "to_char(columnName,'YYYY-MM')"                                                                                           #1947-08
    oracle_format_dict['yy-m']                   = "to_char(columnName,'YYYY-fmMM')"                                                                                         #1947-8
    oracle_format_dict['y-m']                    = "to_char(columnName,'YY-fmMM')"                                                                                           #47-8
    oracle_format_dict['yy-MM-dd']               = date_replace_format.get('yy-MM-dd')                                                                       #1947-March-01
    oracle_format_dict['yy-MM-d']                = "replace((to_char(columnName,'yyyy-Month-FMdd')),' ','')"                                                                 #1947-March-1
    oracle_format_dict['yy-M-dd']                = date_replace_format.get('yy-M-dd')                                                                     #1947-Mar-01
    oracle_format_dict['y-M-dd']                 = date_replace_format.get('y-M-dd')                                                                       #47-Mar-01
    oracle_format_dict['yy-M']                   = date_replace_format.get('yy-M')                                                                        #1947-Mar
    oracle_format_dict['y-M']                    = date_replace_format.get('y-M')                                                                          #47-Mar
    oracle_format_dict['yy-mm-DD']               = date_replace_format.get('yy-mm-DD')                                                                     #1947-08-Friday
    oracle_format_dict['yy-mm-D']                = date_replace_format.get('yy-mm-D')                                                                      #1947-08-Fri
    oracle_format_dict['yy-m-DD']                = "replace((to_char(columnName,'yyyy-fmMM-Dy')),' ','')"
    oracle_format_dict['yy-mm-dd hh:mm:ss']      = "to_char(columnName,'yyyy-mm-dd hh24:MI:ss')"


 # postgres  Formats
    # Note:- 1.Single digit date not available.
    #        2.Single digit month not available.
    postgres_format_dict[DayWeekYear.SUNDAY_WKY_YYYY]       ="concat('WK',to_char(columnName,'ww'),'(',to_char(columnName,'yyyy'),')')"                                        #WK14(1970)
    postgres_format_dict[DayWeekYear.SUNDAY_WKY_YY]         ="concat('WK',to_char(columnName,'ww'),'(',to_char(columnName,'yy'),')')"                                      #WK14(70)
    postgres_format_dict[DayWeekYear.SUNDAY_WK_N_OF_Y_YY]   ="concat('WK ',to_char(columnName,'ww'),' of ',to_char(columnName,'yyyy'))"                                   #WK 14 of 1970
    postgres_format_dict[DayWeekYear.SUNDAY_WEEK_N_OF_Y_YY] ="concat('WeeK ',to_char(columnName,'ww'),' of ',to_char(columnName,'yyyy'))"                                 #Week 14 of 1970
    postgres_format_dict[DayWeekYear.SUNDAY_WEEK_N_OF_MY_YY]="concat('WeeK ',to_char(columnName,'ww'),' of ',to_char(columnName,'Mon-YYYY')) "                            #Week 1 of Jan-1970
    postgres_format_dict[DayWeekYear.MONDAY_WKY_YYYY]       ="concat('WK',to_char(columnName,'IW'),'(',to_char(columnName,'yyyy'),')') "                                   #WK14(1970)
    postgres_format_dict[DayWeekYear.MONDAY_WKY_YY]         ="concat('WK',to_char(columnName,'IW'),'(',to_char(columnName,'yy'),')') "                                     #WK14(70)
    postgres_format_dict[DayWeekYear.MONDAY_WK_N_OF_Y_YY]   ="concat('WeeK ',to_char(columnName,'Iw'),' of ',to_char(columnName,'yyyy')) "                                #WK 14 of 1970
    postgres_format_dict[DayWeekYear.MONDAY_WEEK_N_OF_Y_YY] ="concat('WeeK ',to_char(columnName,'IW'),' of ',to_char(columnName,'yyyy'))"                                 #Week 14 of 1970
    postgres_format_dict[DayWeekYear.MONDAY_WEEK_N_OF_MY_YY]="concat('WeeK ',to_char(columnName,'IW'),' of ',to_char(columnName,'Mon-YYYY')) "                            #Week 1 of Jan-1970
    postgres_format_dict[QuaterYear.CY_QNTH_YY]     ="concat('Quarter', to_char(columnName,'q'),'-',to_char(columnName,'yyyy'))  "                       #Quarter1-1970
    postgres_format_dict[QuaterYear.CY_QNTH_YYYY]             ="concat('Q', to_char(columnName,'q'),'-',to_char(columnName,'yyyy'))  "                             #Q1-1970
    postgres_format_dict[QuaterYear.CY_QNTH_YY]             ="concat('Q', to_char(columnName,'q'),'-',to_char(columnName,'yy'))  "                               #Q1-70
    postgres_format_dict[QuaterYear.FY_QUARTERNTH_YYYY]     ="case when to_char(columnName,'mm') between 4 and 6 then concat('Quarter1','-',to_char(columnName,'yyyy'))\
                                                when to_char(columnName,'mm') between 7 and 9 then concat('Quarter2','-',to_char(columnName,'yyyy'))\
                                                when to_char(columnName,'mm') between 10 and 12  then concat('Quarter3','-',to_char(columnName,'yyyy'))\
                                                else  concat('Quarter4','-',to_char(columnName,'yyyy')) end  "                                      #Quarter1-1970
    postgres_format_dict[QuaterYear.FY_QNTH_YYYY]             ="case when to_char(columnName,'mm') between 4 and 6 then concat('Q1','-',to_char(columnName,'yyyy'))\
                                                 when to_char(columnName,'mm') between 7 and 9 then concat('Q2','-',to_char(columnName,'yyyy'))\
                                                 when to_char(columnName,'mm') between 10 and 12  then concat('Q3','-',to_char(columnName,'yyyy'))\
                                                 else concat('Q4','-',to_char(columnName,'yyyy')) end  "                                             #Q1-1970
    postgres_format_dict[QuaterYear.FY_QNTH_YY]             ="case when to_char(columnName,'mm') between 4 and 6 then concat('Q1','-',to_char(columnName,'yy'))\
                                                 when to_char(columnName,'mm') between 7 and 9 then concat('Q2','-',to_char(columnName,'yy'))\
                                                 when to_char(columnName,'mm') between 10 and 12  then concat('Q3','-',to_char(columnName,'yy'))\
                                                 else  concat('Q4','-',to_char(columnName,'yy')) end  "                                               #Q1-70
    postgres_format_dict['yyyy']                   = dating_format.get('yyyy')                                                                         #1970
    postgres_format_dict['FY-yyyy']                ="case when to_char(columnName,'mm') >=4 then concat(to_char(columnName,'yyyy'),'-',to_char(columnName,'yyyy')+1)\
                                                else concat(to_char(columnName,'yyyy')-1,'-',to_char(columnName,'yyyy')) END "                                     #1969-1970
    postgres_format_dict['y-mm']                    ="To_Char(columnName ,'YY-Mon') "                                                                               #47-Mar
    postgres_format_dict['YY-mm-DD']               =dating_format.get('YY-mm-DD')                                                                           #1947-08-Friday
    postgres_format_dict['YY-mm-D']                =dating_format.get('YY-mm-D')                                                                             #1947-08-Fri
    postgres_format_dict['YY-m-DD']                =dating_format.get('YY-mm-DD')                                                                            #1947-8-Friday
    postgres_format_dict['y-m-DD']                 =dating_format.get('y-m-DD')                                                                              #47-8-Friday
    postgres_format_dict['yy-MM-DD']               =dating_format.get('yy-MM-DD')                                                                    #1947-March-Friday
    postgres_format_dict['yy-MM-D']                =dating_format.get('yy-MM-D')                                                                     #1947-March-Fri
    postgres_format_dict['yy-M-DD']                =dating_format.get('yy-M-DD')                                                                      #1947-Mar-Friday
    postgres_format_dict['y-M-DD']                 =dating_format.get('y-M-DD')                                                                        #47-Mar-Friday
    postgres_format_dict[DayMonthYear.D_M_Y]                    =dating_format.get('D_M_Y')                                                                      #24/10/2020
    postgres_format_dict[DayMonthYear.D_MM_Y]                    = dating_format.get('D_MM_Y')                                                                  #24/October/2020
    postgres_format_dict[DayMonthYear.D_M_Y_SHORT]                    = dating_format.get('D_M_Y_SHORT')                                                                       #24/10/20
    postgres_format_dict['M-Y']                      = dating_format.get('M-Y')                                                                     #October-2020
    postgres_format_dict['m-Y']                      = dating_format.get('m-Y')                                                                        #10-2020
    postgres_format_dict['M-y']                      = dating_format.get('M-y')                                                                       #October-20
    postgres_format_dict['Y-m']                      = dating_format.get('Y-m')                                                                        #2020-10
    postgres_format_dict['Y-M']                      = dating_format.get('Y-M')                                                                     #2020-October
    postgres_format_dict['w-d']                      = dating_format.get('w-d')                                                                             #7
    postgres_format_dict['weekstartdate']            = "date(date_trunc('week',columnName)) "                                                                  #2020-10-19
    postgres_format_dict['weekmonth']                = dating_format.get('weekmonth')                                                                             #4
    #a,b and c here column name, "op" means operator
    postgres_format_dict['changeToLowerCase']       = expressionsDict.get('changeToLowerCase')
    postgres_format_dict['changeToCapitalizeCase']  = expressionsDict.get('changeToCapitalizeCase')
    postgres_format_dict['calculateLength']         = expressionsDict.get('calculateLength')
    postgres_format_dict['changeToUpperCase']       = expressionsDict.get('changeToUpperCase')
    postgres_format_dict['aPlusB']                  = expressionsDict.get('aPlusB')
    postgres_format_dict['aMinusB']                 = expressionsDict.get('aMinusB')
    postgres_format_dict['aMultiplyB']              = expressionsDict.get('aMultiplyB')
    postgres_format_dict['aDivideB']                = expressionsDict.get('aDivideB')
    postgres_format_dict['aPlusBPlusC']             = expressionsDict.get('aPlusBPlusC')
    postgres_format_dict['column1Column2']          =  expressionsDict.get('column1Column2')
    postgres_format_dict['column1Column2Column3']   = expressionsDict.get('column1Column2Column3')
    postgres_format_dict['customExpression']        = ""
    postgres_format_dict['remainderOfADivideB']     = expressionsDict.get('remainderOfADivideB')
    postgres_format_dict['dateAPlusBHours']         = date_time_format.get('dateAPlusBHours')
    postgres_format_dict['dateAPlusBSeconds']       = date_time_format.get('dateAPlusBSeconds')
    postgres_format_dict['dateAPlusBMinutes']       = date_time_format.get('dateAPlusBMinutes')
    postgres_format_dict['dateAPlusBDays']          = date_time_format.get('dateAPlusBDays')
    postgres_format_dict['dateAPlusBMonths']        = date_time_format.get('dateAPlusBMonths')
    postgres_format_dict['dateAMinusBHours']        = "columnName + INTERVAL '-1' hour"
    postgres_format_dict['dateAMinusBSeconds']      = "columnName + INTERVAL '-1' second"
    postgres_format_dict['dateAMinusBMinutes']      = "columnName + INTERVAL '-1' minute"
    postgres_format_dict['dateAMinusBDays']         = "columnName + INTERVAL '-1' day"
    postgres_format_dict['dateAMinusBMonths']       = "columnName + INTERVAL '-1' month"
    postgres_format_dict['compareAequalB']          = ""
    postgres_format_dict['yy-mm-dd']               = dating_format.get('yy-mm-dd')                                                                                        #1947-08-01
    postgres_format_dict['yy-mm-d']                = "to_char(columnName,'yyyy-mm-FMDD')"                                                                                      #1947-08-1
    postgres_format_dict['yy-m-dd']                = "to_char(columnName,'YYYY-fmMM-fmdd')"                                                                                    #1947-8-01
    postgres_format_dict['y-m-dd']                 = "to_char(columnName,'YY-MM-fmdd')"                                                                                        #47-8-01
    postgres_format_dict['yy-mm']                  = "to_char(columnName,'YYYY-MM')"                                                                                           #1947-08
    postgres_format_dict['yy-m']                   = "to_char(columnName,'YYYY-fmMM')"                                                                                         #1947-8
    postgres_format_dict['y-m']                    = "to_char(columnName,'YY-fmMM')"                                                                                           #47-8
    postgres_format_dict['yy-MM-dd']               = date_replace_format.get('yy-MM-dd')                                                                       #1947-March-01
    postgres_format_dict['yy-MM-d']                = "replace((to_char(columnName,'yyyy-Month-FMdd')),' ','')"                                                                 #1947-March-1
    postgres_format_dict['yy-M-dd']                = date_replace_format.get('yy-M-dd')                                                                     #1947-Mar-01
    postgres_format_dict['y-M-dd']                 = date_replace_format.get('y-M-dd')                                                                       #47-Mar-01
    postgres_format_dict['yy-M']                   = date_replace_format.get('yy-M')                                                                        #1947-Mar
    postgres_format_dict['y-M']                    = date_replace_format.get('y-M')                                                                          #47-Mar
    postgres_format_dict['yy-mm-DD']               = date_replace_format.get('yy-mm-DD')                                                                     #1947-08-Friday
    postgres_format_dict['yy-mm-D']                = date_replace_format.get('yy-mm-D')                                                                      #1947-08-Fri
    postgres_format_dict['yy-m-DD']                = "replace((to_char(columnName,'yyyy-fmMM-Dy')),' ','')"
    postgres_format_dict['yy-mm-dd hh:mm:ss']      = "to_char(columnName,'yyyy-mm-dd hh24:MI:ss')"


	# DB2  Formats
    # Note:- 1.Single digit date not available.
    #        2.Single digit month not available.
    db2_format_dict[DayWeekYear.SUNDAY_WKY_YYYY]       ="concat(concat(concat(concat('WK',week(columnName)),'('),to_char(columnName,'yyyy')),')') "                        #WK14(1970)
    db2_format_dict[DayWeekYear.SUNDAY_WKY_YY]         ="concat(concat(concat(concat('WK',week(columnName)),'('),to_char(columnName,'yy')),')')"                         #WK14(70)
    db2_format_dict[DayWeekYear.SUNDAY_WK_N_OF_Y_YY]   ="concat(concat(concat('WK ',week(columnName)),' of '),to_char(columnName,'yyyy'))"                              #WK 14 of 1970
    db2_format_dict[DayWeekYear.SUNDAY_WEEK_N_OF_Y_YY] ="concat(concat(concat('WeeK ',week(columnName)),' of '),to_char(columnName,'yyyy')) "                           #Week 14 of 1970
    db2_format_dict[DayWeekYear.SUNDAY_WEEK_N_OF_MY_YY]="concat(concat(concat('WeeK ',week(columnName)),' of '),to_char(columnName,'Mon-YYYY')) "                       #Week 1 of Jan-1970
    db2_format_dict[DayWeekYear.MONDAY_WKY_YYYY]       ="concat(concat(concat(concat('WK',week_iso(columnName)),'('),to_char(columnName,'yyyy')),')') "                   #WK14(1970)
    db2_format_dict[DayWeekYear.MONDAY_WKY_YY]         ="concat(concat(concat(concat('WK',week_iso(columnName)),'('),to_char(columnName,'yy')),')') "                     #WK14(70)
    db2_format_dict[DayWeekYear.MONDAY_WK_N_OF_Y_YY]   ="concat(concat(concat('WeeK ',week_iso(columnName)),' of '),to_char(columnName,'yyyy')) "                        #WK 14 of 1970
    db2_format_dict[DayWeekYear.MONDAY_WEEK_N_OF_Y_YY] ="concat(concat(concat('WeeK ',week_iso(columnName)),' of '),to_char(columnName,'yyyy')) "                        #Week 14 of 1970
    db2_format_dict[DayWeekYear.MONDAY_WEEK_N_OF_MY_YY]="concat(concat(concat('WeeK ',week_iso(columnName)),' of '),to_char(columnName,'Mon-YYYY')) "                    #Week 1 of Jan-1970
    db2_format_dict[QuaterYear.CY_QNTH_YY]     ="concat(concat(concat('Quarter', to_char(columnName,'q')),'-'),to_char(columnName,'yyyy'))  "         #Quarter1-1970
    db2_format_dict[QuaterYear.CY_QNTH_YYYY]             ="concat(concat(concat('Q', to_char(columnName,'q')),'-'),to_char(columnName,'yyyy'))  "               #Q1-1970
    db2_format_dict[QuaterYear.CY_QNTH_YY]             ="concat(concat(concat('Q', to_char(columnName,'q')),'-'),to_char(columnName,'yy'))  "                 #Q1-70
    db2_format_dict[QuaterYear.FY_QUARTERNTH_YYYY]     ="case when to_char(columnName,'mm') between 4 and 6 then concat(concat('Quarter1','-'),to_char(columnName,'yyyy'))\
                                                when to_char(columnName,'mm') between 7 and 9 then concat(concat('Quarter2','-'),to_char(columnName,'yyyy'))\
                                                when to_char(columnName,'mm') between 10 and 12  then concat(concat('Quarter3','-'),to_char(columnName,'yyyy'))\
                                                else  concat(concat('Quarter4','-'),to_char(columnName,'yyyy')) end  "                              #Quarter1-1970
    db2_format_dict[QuaterYear.FY_QNTH_YYYY]             ="case when to_char(columnName,'mm') between 4 and 6 then concat(concat('Q1','-'),to_char(columnName,'yyyy'))\
                                                 when to_char(columnName,'mm') between 7 and 9 then concat(concat('Q2','-'),to_char(columnName,'yyyy'))\
                                                 when to_char(columnName,'mm') between 10 and 12  then concat(concat('Q3','-'),to_char(columnName,'yyyy'))\
                                                 else  concat(concat('Q4','-'),to_char(columnName,'yyyy')) end  "                                   #Q1-1970
    db2_format_dict[QuaterYear.FY_QNTH_YY]             ="case when to_char(columnName,'mm') between 4 and 6 then concat(concat('Q1','-'),to_char(columnName,'yy'))\
                                                 when to_char(columnName,'mm') between 7 and 9 then concat(concat('Q2','-'),to_char(columnName,'yy'))\
                                                 when to_char(columnName,'mm') between 10 and 12  then concat(concat('Q3','-'),to_char(columnName,'yy'))\
                                                 else  concat(concat('Q4','-'),to_char(columnName,'yy')) end  "                                      #Q1-70
    db2_format_dict['yyyy']                   =dating_format.get('yyyy')                                                                         #1970
    db2_format_dict['FY-yyyy']                ="case when to_char(columnName,'mm') >=4 then concat(concat(to_char(columnName,'yyyy'),'-'),to_char(columnName,'yyyy')+1)\
                                                else concat(concat(to_char(columnName,'yyyy')-1,'-'),to_char(columnName,'yyyy')) END "                             #1969-1970
    db2_format_dict['y-mm']                    ="To_Char(columnName ,'YY-Mon') "                                                                               #47-Mar
    db2_format_dict['YY-mm-DD']               =dating_format.get('YY-mm-DD')                                                                           #1947-08-Friday
    db2_format_dict['YY-mm-D']                =dating_format.get('YY-mm-D')                                                                             #1947-08-Fri
    db2_format_dict['YY-m-DD']                =dating_format.get('YY-mm-DD')                                                                       #1947-8-Friday
    db2_format_dict['y-m-DD']                 =dating_format.get('y-m-DD')                                                                         #47-8-Friday
    db2_format_dict['yy-MM-DD']               =dating_format.get('yy-MM-DD')                                                                    #1947-March-Friday
    db2_format_dict['yy-MM-D']                =dating_format.get('yy-MM-D')                                                                     #1947-March-Fri
    db2_format_dict['yy-M-DD']                =dating_format.get('yy-M-DD')                                                                      #1947-Mar-Friday
    db2_format_dict['y-M-DD']                 =dating_format.get('y-M-DD')                                                                        #47-Mar-Friday
    db2_format_dict[DayMonthYear.D_M_Y]                    =dating_format.get('D_M_Y')                                                                      #24/10/2020
    db2_format_dict[DayMonthYear.D_MM_Y]                    = dating_format.get('D_MM_Y')                                                                  #24/October/2020
    db2_format_dict[DayMonthYear.D_M_Y_SHORT]                    = dating_format.get('D_M_Y_SHORT')                                                                       #24/10/20
    db2_format_dict['M-Y']                      = dating_format.get('M-Y')                                                                     #October-2020
    db2_format_dict['m-Y']                      = dating_format.get('m-Y')                                                                        #10-2020
    db2_format_dict['M-y']                      = dating_format.get('M-y')                                                                       #October-20
    db2_format_dict['Y-m']                      = dating_format.get('Y-m')                                                                        #2020-10
    db2_format_dict['Y-M']                      = dating_format.get('Y-M')                                                                     #2020-October
    db2_format_dict['w-d']                      = "to_char(columnName,'D')"                                                                             #7
    db2_format_dict['weekstartdate']            = "((columnName) - (dayofweek(columnName)-1)  days)"                                                         #2020-10-19
    db2_format_dict['weekmonth']                = "to_char(columnName ,'W')"                                                                             #4
    #a,b and c here column name, "op" means operator
    db2_format_dict['changeToLowerCase']       = expressionsDict.get('changeToLowerCase')
    db2_format_dict['changeToCapitalizeCase']  = expressionsDict.get('changeToCapitalizeCase')
    db2_format_dict['calculateLength']         = expressionsDict.get('calculateLength')
    db2_format_dict['changeToUpperCase']       = expressionsDict.get('changeToUpperCase')
    db2_format_dict['aPlusB']                  = expressionsDict.get('aPlusB')
    db2_format_dict['aMinusB']                 = expressionsDict.get('aMinusB')
    db2_format_dict['aMultiplyB']              = expressionsDict.get('aMultiplyB')
    db2_format_dict['aDivideB']                = expressionsDict.get('aDivideB')
    db2_format_dict['aPlusBPlusC']             = expressionsDict.get('aPlusBPlusC')
    db2_format_dict['column1Column2']          =  expressionsDict.get('column1Column2')
    db2_format_dict['column1Column2Column3']   = expressionsDict.get('column1Column2Column3')
    db2_format_dict['customExpression']        = ""
    db2_format_dict['remainderOfADivideB']     = expressionsDict.get('remainderOfADivideB')
    db2_format_dict['dateAPlusBHours']         = "columnName + 1 hour"
    db2_format_dict['dateAPlusBSeconds']       = "columnName + 1 second"
    db2_format_dict['dateAPlusBMinutes']       = "columnName + 1 minute"
    db2_format_dict['dateAPlusBDays']          = "columnName + 1 day"
    db2_format_dict['dateAPlusBMonths']        = "columnName + 1 month"
    db2_format_dict['dateAMinusBHours']        = "columnName - 1 hour"
    db2_format_dict['dateAMinusBSeconds']      = "columnName - 1 second"
    db2_format_dict['dateAMinusBMinutes']      = "columnName - 1 minute"
    db2_format_dict['dateAMinusBDays']         = "columnName - 1 day"
    db2_format_dict['dateAMinusBMonths']       = "columnName - 1 month"
    db2_format_dict['compareAequalB']          = ""
    db2_format_dict['yy-mm-dd']               = dating_format.get('yy-mm-dd')                                                                                        #1947-08-01
    db2_format_dict['yy-mm-d']                = "concat(to_char(columnName,'yyyy-mm-'),day(columnName))"                                                                     #1947-08-1
    db2_format_dict['yy-m-dd']                = "CONCAT(concat(to_char(columnName,'yyyy-'),MONTH(columnName)),to_char(columnName,'-dd'))"                                       #1947-8-01
    db2_format_dict['y-m-dd']                 = "CONCAT(concat(to_char(columnName,'yy-'),MONTH(columnName)),to_char(columnName,'-dd'))"                                         #47-8-01
    db2_format_dict['yy-mm']                  = "to_char(columnName,'yyyy-mm')"                                                                                           #1947-08
    db2_format_dict['yy-m']                   = "concat(to_char(columnName,'yyyy-'),MONTH(columnName))"                                                                     #1947-8
    db2_format_dict['y-m']                    = "concat(to_char(columnName,'yy-'),MONTH(columnName))"                                                                        #47-8
    db2_format_dict['yy-MM-dd']               = date_replace_format.get('yy-MM-dd')                                                                       #1947-March-01
    db2_format_dict['yy-MM-d']                = "concat(to_char(columnName,'yyyy-Month-'),DAY(columnName))"                                                                  #1947-March-1
    db2_format_dict['yy-M-dd']                = date_replace_format.get('yy-M-dd')                                                                     #1947-Mar-01
    db2_format_dict['y-M-dd']                 = date_replace_format.get('y-M-dd')                                                                       #47-Mar-01
    db2_format_dict['yy-M']                   = date_replace_format.get('yy-M')                                                                        #1947-Mar
    db2_format_dict['y-M']                    = date_replace_format.get('y-M')                                                                          #47-Mar
    db2_format_dict['yy-mm-DD']               = date_replace_format.get('yy-mm-DD')                                                                     #1947-08-Friday
    db2_format_dict['yy-mm-D']                = date_replace_format.get('yy-mm-D')                                                                      #1947-08-Fri
    db2_format_dict['yy-m-DD']                = "CONCAT(concat(to_char(columnName,'yyyy-'),MONTH(columnName)),to_char(columnName,'-Dy'))"                                       #1947-8-Fri


	# teradata  Formats
    # Note:- 1.Single digit date not available.
    #        2.Single digit month not available.
    teradata_format_dict[DayWeekYear.SUNDAY_WKY_YYYY]       ="oreplace(concat('WK',WEEKNUMBER_OF_YEAR(curdate()),'(',to_char(now(),'yyyy'),')'),' ','')"                            #WK14(1970)
    teradata_format_dict[DayWeekYear.SUNDAY_WKY_YY]         ="oreplace(concat('WK',WEEKNUMBER_OF_YEAR(curdate()),'(',to_char(columnName,'yy'),')'),' ','')"                            #WK14(70)
    teradata_format_dict[DayWeekYear.SUNDAY_WK_N_OF_Y_YY]   ="concat('WK ',trim(WEEKNUMBER_OF_YEAR(curdate())),' of ',to_char(now(),'yyyy'))"                                      #WK 14 of 1970
    teradata_format_dict[DayWeekYear.SUNDAY_WEEK_N_OF_Y_YY] ="concat('WeeK ',trim(WEEKNUMBER_OF_YEAR(curdate())),' of ',to_char(columnName,'yyyy'))"                                   #Week 14 of 1970
    teradata_format_dict[DayWeekYear.SUNDAY_WEEK_N_OF_MY_YY]="concat('WeeK ',trim(WEEKNUMBER_OF_YEAR(curdate())),' of ',to_char(columnName,'Mon-YYYY')) "                              #Week 1 of Jan-1970
    teradata_format_dict[DayWeekYear.MONDAY_WKY_YYYY]       ="concat('WK',trim(WEEKNUMBER_OF_YEAR(curdate(),'ISO')),'(',to_char(columnName,'yyyy'),')') "                               #WK14(1970)
    teradata_format_dict[DayWeekYear.MONDAY_WKY_YY]         ="concat('WK',trim(WEEKNUMBER_OF_YEAR(curdate(),'ISO')),'(',to_char(columnName,'yy'),')') "                                 #WK14(70)
    teradata_format_dict[DayWeekYear.MONDAY_WK_N_OF_Y_YY]   ="concat('WeeK ',trim(WEEKNUMBER_OF_YEAR(curdate(),'ISO')),' of ',to_char(columnName,'yyyy')) "                            #WK 14 of 1970
    teradata_format_dict[DayWeekYear.MONDAY_WEEK_N_OF_Y_YY] ="concat('WeeK ',trim(WEEKNUMBER_OF_YEAR(curdate(),'ISO')),' of ',to_char(columnName,'yyyy'))"                             #Week 14 of 1970
    teradata_format_dict[DayWeekYear.MONDAY_WEEK_N_OF_MY_YY]="concat('WeeK ',trim(WEEKNUMBER_OF_YEAR(curdate(),'ISO')),' of ',to_char(columnName,'Mon-YYYY')) "                        #Week 1 of Jan-1970
    teradata_format_dict[QuaterYear.CY_QNTH_YY]     ="concat('Quarter', to_char(columnName,'q'),'-',to_char(columnName,'yyyy'))  "                                       #Quarter1-1970
    teradata_format_dict[QuaterYear.CY_QNTH_YYYY]             ="concat('Q', to_char(columnName,'q'),'-',to_char(columnName,'yyyy'))  "                                             #Q1-1970
    teradata_format_dict[QuaterYear.CY_QNTH_YY]             ="concat('Q', to_char(columnName,'q'),'-',to_char(columnName,'yy'))  "                                                #Q1-70
    teradata_format_dict[QuaterYear.FY_QUARTERNTH_YYYY]     ="case when to_char(columnName,'mm') between 4 and 6 then concat('Quarter1','-',to_char(columnName,'yyyy'))\
                                                when to_char(columnName,'mm') between 7 and 9 then concat('Quarter2','-',to_char(columnName,'yyyy'))\
                                                when to_char(columnName,'mm') between 10 and 12  then concat('Quarter3','-',to_char(columnName,'yyyy'))\
                                                else  concat('Quarter4','-',to_char(columnName,'yyyy')) end  "                                                     #Quarter1-1970
    teradata_format_dict[QuaterYear.FY_QNTH_YYYY]             ="case when to_char(columnName,'mm') between 4 and 6 then concat('Q1','-',to_char(columnName,'yyyy'))\
                                                 when to_char(columnName,'mm') between 7 and 9 then concat('Q2','-',to_char(columnName,'yyyy'))\
                                                 when to_char(columnName,'mm') between 10 and 12  then concat('Q3','-',to_char(columnName,'yyyy'))\
                                                 else concat('Q4','-',to_char(columnName,'yyyy')) end  "                                                            #Q1-1970
    teradata_format_dict[QuaterYear.FY_QNTH_YY]             ="case when to_char(columnName,'mm') between 4 and 6 then concat('Q1','-',to_char(columnName,'yy'))\
                                                 when to_char(columnName,'mm') between 7 and 9 then concat('Q2','-',to_char(columnName,'yy'))\
                                                 when to_char(columnName,'mm') between 10 and 12  then concat('Q3','-',to_char(columnName,'yy'))\
                                                 else  concat('Q4','-',to_char(columnName,'yy')) end  "                                                              #Q1-70
    teradata_format_dict['yyyy']                   =dating_format.get('yyyy')                                                                                       #1970
    teradata_format_dict['FY-yyyy']                ="case when to_char(curdate(),'mm') >=4 then oreplace(concat(to_char(curdate(),'yyyy'),'-',(cast(to_char(curdate(),'yyyy') as integer)+1)),' ','')\
                                                  else right(concat(cast(to_char(curdate(),'yyyy') as integer) -1,'-',to_char(curdate(),'yyyy')),9) END"                   #1969-1970
    teradata_format_dict['y-mm']                    ="To_Char(columnName ,'YY-Mon')"                                                                                             #47-Mar
    teradata_format_dict['YY-mm-DD']               =dating_format.get('YY-mm-DD')                                                                                        #1947-08-Friday
    teradata_format_dict['YY-mm-D']                =dating_format.get('YY-mm-D')                                                                                         #1947-08-Fri
    teradata_format_dict['YY-m-DD']                =dating_format.get('YY-mm-DD')                                                                                        #1947-8-Friday
    teradata_format_dict['y-m-DD']                 =dating_format.get('y-m-DD')                                                                                          #47-8-Friday
    teradata_format_dict['yy-MM-DD']               =dating_format.get('yy-MM-DD')                                                                                     #1947-March-Friday
    teradata_format_dict['yy-MM-D']                ="oreplace(To_Char(columnName,'YY-Month-Dy'),' ','')"                                                                        #1947-March-Fri
    teradata_format_dict['yy-M-DD']                =dating_format.get('yy-M-DD')                                                                                       #1947-Mar-Friday
    teradata_format_dict['y-M-DD']                 =dating_format.get('y-M-DD')                                                                                         #47-Mar-Friday
    teradata_format_dict[DayMonthYear.D_M_Y]                    =dating_format.get('D_M_Y')                                                                                       #24/10/2020
    teradata_format_dict[DayMonthYear.D_MM_Y]                    = "oreplace(To_Char(columnName,'dd/month/yyyy'),' ','')"                                                                   #24/October/2020
    teradata_format_dict[DayMonthYear.D_M_Y_SHORT]                    = dating_format.get('D_M_Y_SHORT')                                                                                        #24/10/20
    teradata_format_dict['M-Y']                      = "oreplace(To_Char(columnName,'month-yyyy'),' ','')"                                                                      #October-2020
    teradata_format_dict['m-Y']                      = dating_format.get('m-Y')                                                                                         #10-2020
    teradata_format_dict['M-y']                      = "oreplace(To_Char(columnName,'month-yy'),' ','')"                                                                        #October-20
    teradata_format_dict['Y-m']                      = dating_format.get('Y-m')                                                                                         #2020-10
    teradata_format_dict['Y-M']                      = "oreplace(To_Char(columnName,'yyyy-month'),' ','')"                                                                      #2020-October
    teradata_format_dict['w-d']                      = dating_format.get('w-d')                                                                                              #7
    teradata_format_dict['weekstartdate']            = "ROUND(columnName, 'D') (FORMAT 'yyyy-mm-dd') "                                                                          #2020-10-19
    teradata_format_dict['weekmonth']                = dating_format.get('weekmonth')                                                                                              #4
    #a,b and c here column name, "op" means operator
    teradata_format_dict['changeToLowerCase']       = expressionsDict.get('changeToLowerCase')
    teradata_format_dict['changeToCapitalizeCase']  = expressionsDict.get('changeToCapitalizeCase')
    teradata_format_dict['calculateLength']         = expressionsDict.get('calculateLength')
    teradata_format_dict['changeToUpperCase']       = expressionsDict.get('changeToUpperCase')
    teradata_format_dict['aPlusB']                  = expressionsDict.get('aPlusB')
    teradata_format_dict['aMinusB']                 = expressionsDict.get('aMinusB')
    teradata_format_dict['aMultiplyB']              = expressionsDict.get('aMultiplyB')
    teradata_format_dict['aDivideB']                = expressionsDict.get('aDivideB')
    teradata_format_dict['aPlusBPlusC']             = expressionsDict.get('aPlusBPlusC')
    teradata_format_dict['column1Column2']          =  expressionsDict.get('column1Column2')
    teradata_format_dict['column1Column2Column3']   = expressionsDict.get('column1Column2Column3')
    teradata_format_dict['customExpression']        = ""
    teradata_format_dict['remainderOfADivideB']     = expressionsDict.get('remainderOfADivideB')
    teradata_format_dict['dateAPlusBHours']         = date_time_format.get('dateAPlusBHours')
    teradata_format_dict['dateAPlusBSeconds']       = date_time_format.get('dateAPlusBSeconds')
    teradata_format_dict['dateAPlusBMinutes']       = date_time_format.get('dateAPlusBMinutes')
    teradata_format_dict['dateAPlusBDays']          = date_time_format.get('dateAPlusBDays')
    teradata_format_dict['dateAPlusBMonths']        = date_time_format.get('dateAPlusBMonths')
    teradata_format_dict['dateAMinusBHours']        = "columnName - INTERVAL '1' hour"
    teradata_format_dict['dateAMinusBSeconds']      = "columnName - INTERVAL '1' second"
    teradata_format_dict['dateAMinusBMinutes']      = "columnName - INTERVAL '1' minute"
    teradata_format_dict['dateAMinusBDays']         = "columnName - INTERVAL '1' day"
    teradata_format_dict['dateAMinusBMonths']       = "columnName - INTERVAL '1' month"
    teradata_format_dict['compareAequalB']          = ""
    teradata_format_dict['yy-mm-dd']                = dating_format.get('yy-mm-dd')                                                                                        #1947-08-01
    teradata_format_dict['yy-mm-d']                 = "to_char(columnName,'yyyy-mm-fmdd')"                                                                                      #1947-08-1
    teradata_format_dict['yy-m-dd']                 = "to_char(columnName,'yyyy-fmmm-fmdd')"                                                                                    #1947-8-01
    teradata_format_dict['y-m-dd']                  = "to_char(columnName,'yy-fmmm-fmdd')"                                                                                      #47-8-01
    teradata_format_dict['yy-mm']                   = "to_char(columnName,'yyyy-mm')"                                                                                           #1947-08
    teradata_format_dict['yy-m']                    = "to_char(columnName,'yyyy-fmmm')"                                                                                         #1947-8
    teradata_format_dict['y-m']                     = "to_char(columnName,'yy-fmmm')"                                                                                           #47-8
    teradata_format_dict['yy-MM-dd']                = "oreplace(to_char(columnName,'yyyy-Month-dd'),' ','') "                                                                   #1947-March-01
    teradata_format_dict['yy-MM-d']                 = "oreplace(to_char(columnName,'yyyy-Month-fmdd'),' ','') "                                                                 #1947-March-1
    teradata_format_dict['yy-M-dd']                 = "oreplace((to_char(columnName,'yyyy-Mon-dd')),' ','')"                                                                     #1947-Mar-01
    teradata_format_dict['y-M-dd']                  = "oreplace((to_char(columnName,'yy-Mon-dd')),' ','')"                                                                       #47-Mar-01
    teradata_format_dict['yy-M']                    = "oreplace((to_char(columnName,'yyyy-Mon')),' ','')"                                                                        #1947-Mar
    teradata_format_dict['y-M']                     = "oreplace((to_char(columnName,'yy-Mon')),' ','')"                                                                          #47-Mar
    teradata_format_dict['yy-mm-DD']                = "oreplace((to_char(columnName,'yyyy-MM-Day')),' ','')"                                                                     #1947-08-Friday
    teradata_format_dict['yy-mm-D']                 = date_replace_format.get('yy-mm-D')                                                                      #1947-08-Fri
    teradata_format_dict['yy-m-DD']                 = "oreplace(to_char(columnName,'yyyy-fmMM-Dy'),' ','')"                                                                     #1947-8-Fri


    format_string_dict['MYSQL']=mysql_format_dict
    format_string_dict['SQLSERVER']=mssql_format_dict
    format_string_dict['VERTICA']=vertica_format_dict
    format_string_dict['ORACLE']=oracle_format_dict
    format_string_dict['TERADATA']=teradata_format_dict
    format_string_dict['POSTGRES']=postgres_format_dict
    format_string_dict['DB2']=db2_format_dict
    format_string_dict['ATHENA']=mssql_format_dict
    format_string_dict['REDSHIFT']=postgres_format_dict

    #HIVE and SQREAM in progress...
    #In TODO LIST
    format_string_dict['HIVE']=oracle_format_dict
    format_string_dict['SQREAM']=oracle_format_dict

    @staticmethod
    def get_dbdate_format(db_type=None, format_string=None):
        if db_type==None or db_type=='':
            raise ValueError("db_type parameter is required.")
        if format_string==None or format_string=='':
            raise ValueError("format_string parameter is required.")

        return GetDBDateFormat.format_string_dict[db_type][format_string]
