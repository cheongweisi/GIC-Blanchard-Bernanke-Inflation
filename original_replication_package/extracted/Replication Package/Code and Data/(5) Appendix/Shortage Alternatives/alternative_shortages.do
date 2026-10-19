*****************************CHANGE PATH HERE***********************************
* Note: change the filepath the the data folder on your computer
clear all 
clear matrix

* Input Location - ImportData.dta
use "..\Replication Package\Code and Data\(1) Data\Public Data\Regression_Data.dta", replace

* Output Location
cd "..\Replication Package\Code and Data\(5) Appendix\Shortage Alternatives"

*********************************************************************************

**** First Specification: NY Fed 

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
gen cf1 = EXPINF1YR
gen cf10 = EXPINF10YR
	* Shortage 2019 average
gen shortage = GSCPI
replace shortage=-.035 if shortage==. 
	* Catchup term
gen diffcpicf  = 0.25*(gcpi+l1.gcpi + l2.gcpi + l3.gcpi) -l4.cf1
	
* Add dummy variables for covid.
gen dummyq2_2020 = 0.0
replace dummyq2_2020 = 1.0 if period==tq(2020:2)

gen dummyq3_2020 = 0.0
replace dummyq3_2020 = 1.0 if period==tq(2020:3)

* REGRESSIONS 
global WAGE "gw"
global CF1 "cf1"
global CF10 "cf10"
global GCPI "gcpi"

keep period gcpi vu gw magpty grpe grpf cf1 cf10 shortage diffcpicf CPIENGSL CPIUFDSL dummyq2_2020 dummyq3_2020
keep if period>=tq(1989:1) & period<=tq(2023:2)


*******gcpi*********************************************************************
constraint define 2 l1.gcpi + l2.gcpi + l3.gcpi + l4.gcpi + gw + l1.gw + l2.gw + l3.gw + l4.gw =1
cnsreg $GCPI magpty l1.gcpi l2.gcpi l3.gcpi l4.gcpi gw l1.gw l2.gw l3.gw l4.gw grpe l1.grpe l2.grpe l3.grpe l4.grpe grpf l1.grpf l2.grpf l3.grpf l4.grpf shortage l1.shortage l2.shortage l3.shortage l4.shortage, c(2)

outreg2 using ny_fed_reg.doc, replace ctitle(gcpi (NY Fed)) 

eststo col2
predict gcpif
gen gcpi_residuals =  gcpi - gcpif

	* Save coefficients in excel format 
putexcel set "eq_coefficients", modify sheet("gcpi_nyfed", replace)
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
putexcel set "summary_stats", modify sheet("gcpi_nyfed", replace)
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






* Note: change the filepath the the data folder on your computer
clear all 
clear matrix

* Input Location - ImportData.dta
use "C:\Users\SBoocker\Dropbox\Bernanke_Blanchard\AEJ Macro\Replication Package\Code and Data\(1) Data\Public Data\Regression_Data.dta", replace

* Output Location
cd "C:\Users\SBoocker\Dropbox\Bernanke_Blanchard\AEJ Macro\Replication Package\Code and Data\(5) Appendix\Shortage Alternatives"

*********************************************************************************
