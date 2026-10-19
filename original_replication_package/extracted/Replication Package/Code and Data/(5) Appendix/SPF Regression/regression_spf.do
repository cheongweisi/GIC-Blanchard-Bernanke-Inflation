* What Caused the U.S Pandemic-Era Inflation? Bernanke, Blanchard 2023 
* This version : October 12, 2023
* Please contact Sam Boocker (Brookings Institution) for further questions. 

* This file runs simulations (empirical model) using ImportData.dta 
* In this file, we use CPI to calculate grpe and grpf.

*****************************CHANGE PATH HERE***********************************
* Note: change the filepath the the data folder on your computer
clear all 
clear matrix

* Input Location - ImportData.dta
use "..\Replication Package\Code and Data\(1) Data\Public Data\Regression_Data.dta", replace 

* Output Location
cd "..\Replication Package\Code and Data\(5) Appendix\SPF Regression\"

*********************************************************************************

* QUARTERLY TIME VARIABLE 
gen period = quarterly(Date, "YQ")
format period %tq
drop Date
order period
tsset period

* DATA MANIPULATION 
gen gcpi = 400*(ln(CPIAUCSL)-ln(l1.CPIAUCSL))
gen gw = 400*(ln(ECIWAG)-ln(l1.ECIWAG))
gen gpty = 400*(ln(OPHNFB)-ln(l1.OPHNFB))
gen magpty = 0.125*(gpty + l1.gpty + l2.gpty + l3.gpty + l4.gpty + l5.gpty + l6.gpty + l7.gpty )

gen rpe = CPIENGSL/ECIWAG
gen rpf = CPIUFDSL/ECIWAG
gen grpe = 400*(ln(rpe)-ln(l1.rpe))
gen grpf = 400*(ln(rpf)-ln(l1.rpf))
gen vu = VOVERU

destring SPF1YR, replace ignore("#N/A")
gen spf1 = SPF1YR

destring SPF10YR, replace ignore("#N/A")
gen spf10 = SPF10YR

	* Shortage
gen shortage = SHORTAGE
replace shortage=5 if shortage==.
	* Catchup term
gen diffcpicf  = 0.25*(gcpi+l1.gcpi + l2.gcpi + l3.gcpi) -l4.spf1
	
* Add dummy variables for covid.
gen dummyq2_2020 = 0.0
replace dummyq2_2020 = 1.0 if period==tq(2020:2)

gen dummyq3_2020 = 0.0
replace dummyq3_2020 = 1.0 if period==tq(2020:3)

* REGRESSIONS 
global WAGE "gw"
global spf1 "spf1"
global spf10 "spf10"
global gcpi "gcpi"

keep period gcpi vu gw magpty grpe grpf spf1 spf10 shortage diffcpicf CPIENGSL CPIUFDSL dummyq2_2020 dummyq3_2020
keep if period>=tq(1989:1) & period<=tq(2023:2)

********gw**********************************************************************
constraint define 1  l1.gw + l2.gw + l3.gw + l4.gw + l1.spf1 + l2.spf1 + l3.spf1 + l4.spf1 = 1
cnsreg $WAGE l1.gw l2.gw l3.gw l4.gw l1.spf1 l2.spf1 l3.spf1 l4.spf1 l1.magpty l1.vu l2.vu l3.vu l4.vu l1.diffcpicf l2.diffcpicf l3.diffcpicf l4.diffcpicf dummyq2_2020 dummyq3_2020, c(1)
eststo col1
predict gwf1
gen gw_residuals = gw-gwf1

	* Save coefficients in excel format 
putexcel set "eq_coefficients_spf", replace sheet("gw")
putexcel B1 = "beta"
matrix b = e(b)'
putexcel A2 = matrix(b), rownames nformat(number_d7)

	* Compute sum of coefficients 
gen aa1 = _b[l1.gw] + _b[l2.gw] + _b[l3.gw] + _b[l4.gw]  
gen bb1 = _b[l1.vu] + _b[l2.vu] + _b[l3.vu] + _b[l4.vu]  
gen cc1 = _b[l1.diffcpicf] + _b[l2.diffcpicf] + _b[l3.diffcpicf] + _b[l4.diffcpicf]
gen dd1 = _b[l1.spf1] + _b[l2.spf1] + _b[l3.spf1] + _b[l4.spf1]
list aa1 bb1 cc1 dd1 if period == tq(2019:1)  

	* P-value (sum)
putexcel set "summary_stats_spf", replace sheet("gw")
putexcel B1 = "sum of coefficients"
putexcel B1 = "sum of coefficients"
putexcel C1 = "p value (sum)"
putexcel D1 = "p value (joint)"
putexcel A2 = "l1.gw1 through l4.gw1"
putexcel A3 = "l1.spf1 through l4.spf1"
putexcel A4 = "l1.vu through l4.vu"
putexcel A5 = "l1.diffcpicf through l4.diffcpicf"
putexcel A6 = "l1.magpty"
putexcel A8 = "R2"
putexcel A9 = "number of observations"

test _b[l1.gw] + _b[l2.gw] + _b[l3.gw] + _b[l4.gw]  = 0
matrix b = r(p)'
putexcel B2 = aa1
putexcel C2 = matrix(b), nformat(number_d7)                                          

test _b[l1.spf1] + _b[l2.spf1] + _b[l3.spf1] + _b[l4.spf1] = 0
matrix b = r(p)'
putexcel B3 = dd1
putexcel C3 = matrix(b), nformat(number_d7)

test _b[l1.vu] + _b[l2.vu] + _b[l3.vu] + _b[l4.vu] = 0
matrix b = r(p)'
putexcel B4 = bb1
putexcel C4 = matrix(b), nformat(number_d7)  

test _b[l1.diffcpicf] + _b[l2.diffcpicf] + _b[l3.diffcpicf] + _b[l4.diffcpicf] = 0
matrix b = r(p)'
putexcel B5 = cc1
putexcel C5 = matrix(b), nformat(number_d7) 

putexcel B6 = _b[l1.magpty]
 				   					   
	* P-value(joint)
test l1.gw l2.gw l3.gw l4.gw 
matrix b = r(p)'
putexcel D2 = matrix(b), nformat(number_d7)  
   
test l1.spf1 l2.spf1 l3.spf1 l4.spf1
matrix b = r(p)'
putexcel D3 = matrix(b), nformat(number_d7) 
   
test l1.vu l2.vu l3.vu l4.vu
matrix b = r(p)'
putexcel D4 = matrix(b), nformat(number_d7)    

test l1.diffcpicf l2.diffcpicf l3.diffcpicf l4.diffcpicf
matrix b = r(p)'
putexcel D5 = matrix(b), nformat(number_d7)    

test l1.magpty
matrix b = r(p)'
putexcel D6 = matrix(b), nformat(number_d7)

corr gw gwf1 if period>=tq(1990:1) 
gen r2aa = r(rho)^2
putexcel B8 = r2aa

gen n_obsaa = e(N)
putexcel B9 = n_obsaa

*******gcpi*********************************************************************
constraint define 2 l1.gcpi + l2.gcpi + l3.gcpi + l4.gcpi + gw + l1.gw + l2.gw + l3.gw + l4.gw =1
cnsreg $gcpi magpty l1.gcpi l2.gcpi l3.gcpi l4.gcpi gw l1.gw l2.gw l3.gw l4.gw grpe l1.grpe l2.grpe l3.grpe l4.grpe grpf l1.grpf l2.grpf l3.grpf l4.grpf shortage l1.shortage l2.shortage l3.shortage l4.shortage, c(2)
eststo col2
predict gcpif
gen gcpi_residuals =  gcpi - gcpif

	* Save coefficients in excel format 
putexcel set "eq_coefficients_spf", modify sheet("gcpi", replace)
putexcel B1 = "beta"
putexcel B1 = "beta"
matrix b = e(b)'
putexcel A2 = matrix(b), rownames nformat(number_d7)

	* Compute sum of coefficients 
gen aa2 = _b[l1.gcpi] + _b[l2.gcpi] + _b[l3.gcpi] + _b[l4.gcpi] 
gen bb2 = _b[gw] + _b[l1.gw] + _b[l2.gw] + _b[l3.gw] + _b[l4.gw]
gen cc2 = _b[grpe] + _b[l1.grpe] + _b[l2.grpe] + _b[l3.grpe] + _b[l4.grpe]
gen dd2 = _b[grpf] + _b[l1.grpf] + _b[l2.grpf] + _b[l3.grpf] + _b[l4.grpf]
gen ee2 = _b[shortage] + _b[l1.shortage] + _b[l2.shortage] + _b[l3.shortage] +_b[l4.shortage]
list period aa2 bb2 cc2 dd2 ee2 if period == tq(2019:1)

	* P-value (sum)
putexcel set "summary_stats_spf", modify sheet("gcpi", replace)
putexcel B1 = "sum of coefficients"
putexcel B1 = "sum of coefficients"
putexcel C1 = "p value (sum)"
putexcel D1 = "p value (joint)"
putexcel A2 = "l1.gcpi through l4.gcpi"
putexcel A3 = "gw through l4.gw"
putexcel A4 = "grpe through l4.grpe"
putexcel A5 = "grpf through l4.grpf"
putexcel A6 = "shortage through l4.shortage"
putexcel A7 = "magpty"
putexcel A9 = "R2"
putexcel A10 = "number of observations"

test _b[l1.gcpi] + _b[l2.gcpi] + _b[l3.gcpi] + _b[l4.gcpi] =0
matrix b = r(p)'
putexcel B2 = aa2
putexcel C2 = matrix(b), nformat(number_d7)

test _b[gw] + _b[l1.gw] + _b[l2.gw] + _b[l3.gw] + _b[l4.gw] =0 
matrix b = r(p)'
putexcel B3 = bb2
putexcel C3 = matrix(b), nformat(number_d7) 

test _b[grpe] + _b[l1.grpe] + _b[l2.grpe] + _b[l3.grpe] + _b[l4.grpe] = 0
matrix b = r(p)'
putexcel B4 = cc2
putexcel C4 = matrix(b), nformat(number_d7)

test _b[grpf] + _b[l1.grpf] + _b[l2.grpf] + _b[l3.grpf] + _b[l4.grpf] = 0
matrix b = r(p)'
putexcel B5 = dd2
putexcel C5 = matrix(b), nformat(number_d7)

test _b[shortage] + _b[l1.shortage] + _b[l2.shortage] + _b[l3.shortage] +_b[l4.shortage] = 0 
matrix b = r(p)'
putexcel B6 = ee2
putexcel C6 = matrix(b), nformat(number_d7)

putexcel B7 = _b[magpty]


	* P-value(joint)
test l1.gcpi l2.gcpi l3.gcpi l4.gcpi
matrix b = r(p)'
putexcel D2 = matrix(b), nformat(number_d7)

test gw l1.gw l2.gw l3.gw l4.gw 
matrix b = r(p)'
putexcel D3 = matrix(b), nformat(number_d7)

test grpe l1.grpe l2.grpe l3.grpe l4.grpe 
matrix b = r(p)'
putexcel D4 = matrix(b), nformat(number_d7)

test grpf l1.grpf l2.grpf l3.grpf l4.grpf 
matrix b = r(p)'
putexcel D5 = matrix(b), nformat(number_d7)

test shortage l1.shortage l2.shortage l3.shortage l4.shortage
matrix b = r(p)'
putexcel D6 = matrix(b), nformat(number_d7)

test magpty
matrix b = r(p)'
putexcel D7 = matrix(b), nformat(number_d7)


corr gcpi gcpif if period>=tq(1990:1)
gen r2bb = r(rho)^2
putexcel B9 = r2bb

gen n_obsbb = e(N)
putexcel B10 = n_obsbb


*******spf1**********************************************************************
constraint define 3 l1.spf1 + l2.spf1 +l3.spf1 +l4.spf1 +spf10 +l1.spf10 +l2.spf10 +l3.spf10 +l4.spf10 +gcpi +l1.gcpi +l2.gcpi +l3.gcpi +l4.gcpi = 1.0
cnsreg $spf1 l1.spf1 l2.spf1 l3.spf1 l4.spf1 spf10 l1.spf10 l2.spf10 l3.spf10 l4.spf10 gcpi l1.gcpi l2.gcpi l3.gcpi l4.gcpi, c(3) noconstant
eststo col3
predict spf1f
gen spf1_residuals = spf1-spf1f

	* Save coefficients in excel format
putexcel set "eq_coefficients_spf", modify sheet("spf1", replace)
putexcel B1 = "beta"
putexcel B1 = "beta"
matrix b = e(b)'
putexcel A2 = matrix(b), rownames nformat(number_d7)
	* Compute sum of coefficients 
gen aa3 = _b[l1.spf1] + _b[l2.spf1] + _b[l3.spf1]+ _b[l4.spf1]
gen bb3 = _b[spf10] +_b[l1.spf10] + _b[l2.spf10] + _b[l3.spf10] + _b[l4.spf10]
gen cc3 = _b[gcpi]+_b[l1.gcpi] + _b[l2.gcpi] +  _b[l3.gcpi] + _b[l4.gcpi]
list period aa3 bb3 cc3 if period==tq(2019:1) 
	* P-value (sum)
putexcel set "summary_stats_spf", modify sheet("spf1", replace)
putexcel B1 = "sum of coefficients"
putexcel B1 = "sum of coefficients"
putexcel C1 = "p value (sum)"
putexcel D1 = "p value (joint)"
putexcel A2 = "l1.spf1 through l4.spf1"
putexcel A3 = "spf10 through l4.spf10"
putexcel A4 = "gcpi through l4.gcpi"
putexcel A6 = "R2"
putexcel A7 = "number of observations"

test _b[l1.spf1] + _b[l2.spf1] + _b[l3.spf1]+ _b[l4.spf1] = 0
matrix b = r(p)'
putexcel B2 = aa3
putexcel C2 = matrix(b), nformat(number_d7) 

test _b[spf10] +_b[l1.spf10] + _b[l2.spf10] + _b[l3.spf10] + _b[l4.spf10] = 0 
matrix b = r(p)'
putexcel B3 = bb3
putexcel C3 = matrix(b), nformat(number_d7) 

test _b[gcpi]+_b[l1.gcpi] + _b[l2.gcpi] +  _b[l3.gcpi] + _b[l4.gcpi] = 0
matrix b = r(p)'
putexcel B4 = cc3
putexcel C4 = matrix(b), nformat(number_d7) 

	* P-value(joint)
test l1.spf1 l2.spf1 l3.spf1 l4.spf1 
matrix b = r(p)'
putexcel D2 = matrix(b), nformat(number_d7) 

test spf10 l1.spf10 l2.spf10 l3.spf10 l4.spf10
matrix b = r(p)'
putexcel D3 = matrix(b), nformat(number_d7)

test gcpi l1.gcpi l2.gcpi l3.gcpi l4.gcpi
matrix b = r(p)'
putexcel D4 = matrix(b), nformat(number_d7)

corr spf1 spf1f if period>=tq(1990:1)
gen r2cc = r(rho)^2
putexcel B6 = r2cc

gen n_obscc = e(N)
putexcel B7 = n_obscc

*******spf10*********************************************************************
constraint define 4 l1.spf10 +l2.spf10 +l3.spf10 + l4.spf10 + gcpi +l1.gcpi +l2.gcpi + l3.gcpi + l4.gcpi = 1.0
cnsreg $spf10 l1.spf10 l2.spf10 l3.spf10 l4.spf10 gcpi l1.gcpi l2.gcpi l3.gcpi l4.gcpi, c(4) noconstant
eststo col4
predict spf10f
gen spf10_residuals = spf10f-spf10 
	* Save coefficients in excel format
putexcel set "eq_coefficients_spf", modify sheet("spf10", replace)
putexcel B1 = "beta"
putexcel B1 = "beta"
matrix b = e(b)'
putexcel A2 = matrix(b), rownames nformat(number_d7)
	* Compute sum of coefficients 
gen aa4 = _b[l1.spf10] + _b[l2.spf10] + _b[l3.spf10] + _b[l4.spf10]
gen bb4 = _b[gcpi] + _b[l1.gcpi] + _b[l2.gcpi] + _b[l3.gcpi] + _b[l4.gcpi]
list period aa4 bb4 if period == tq(2019:1) 
	* P-value (sum)
putexcel set "summary_stats_spf", modify sheet("spf10", replace)
putexcel B1 = "sum of coefficients"
putexcel B1 = "sum of coefficients"
putexcel C1 = "p value (sum)"
putexcel D1 = "p value (joint)"
putexcel A2 = "l1.spf10 through l4.spf10"
putexcel A3 = "gcpi through l4.gcpi"
putexcel A5 = "R2"
putexcel A6 = "number of observations"

test _b[l1.spf10] + _b[l2.spf10] + _b[l3.spf10] + _b[l4.spf10] = 0 
matrix b = r(p)'
putexcel B2 = aa4
putexcel C2 = matrix(b), nformat(number_d7)

test _b[gcpi] + _b[l1.gcpi] + _b[l2.gcpi] + _b[l3.gcpi] + _b[l4.gcpi] = 0 
matrix b = r(p)'
putexcel B3 = bb4
putexcel C3 = matrix(b), nformat(number_d7)

	* P-value(joint)
test l1.spf10 l2.spf10 l3.spf10 l4.spf10
matrix b = r(p)'
putexcel D2 = matrix(b), nformat(number_d7)

test gcpi l1.gcpi l2.gcpi l3.gcpi l4.gcpi 
matrix b = r(p)'
putexcel D3 = matrix(b), nformat(number_d7)

corr spf10 spf10f if period>=tq(1990:1)
gen r2dd = r(rho)^2
putexcel B5 = r2dd

gen n_obsdd = e(N)
putexcel B6 = n_obsdd

* Export Data
drop aa1 bb1 cc1 dd1 aa2 bb2 cc2 dd2 ee2 aa3 bb3 cc3 aa4 bb4
export excel eq_simulations_data_spf, firstrow(variables) replace
