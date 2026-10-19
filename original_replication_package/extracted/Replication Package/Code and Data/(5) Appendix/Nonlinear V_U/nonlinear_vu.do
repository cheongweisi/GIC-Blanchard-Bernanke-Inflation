* What Caused the U.S Pandemic-Era Inflation? Bernanke, Blanchard 2023 
* This version : October 12, 2023
* Please contact Sam Boocker (Brookings Institution) for further questions. 

* This file runs simulations (empirical model) using ImportData.dta 
* In this file, we use CPI to calculate grpe and grpf.

*****************************CHANGE PATH HERE***********************************
* Note: change the filepath the the data folder on your computer
use "../Replication Package/Code and Data/(1) Data/Public Data/Regression_Data.dta", replace

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
gen cf1 = EXPINF1YR
gen cf10 = EXPINF10YR

* Shortage
gen shortage = SHORTAGE
replace shortage=5 if shortage==.

* Catchup term
gen diffcpicf  = 0.25*(gcpi+l1.gcpi + l2.gcpi + l3.gcpi) -l4.cf1
	
* Add dummy variables for covid.
gen dummyq2_2020 = 0.0
replace dummyq2_2020 = 1.0 if period==tq(2020:2)

gen dummyq3_2020 = 0.0
replace dummyq3_2020 = 1.0 if period==tq(2020:3)

* Add dummy variable to test for nonlinearity of vu. 
gen dummy_vu = 0.0
replace dummy_vu = 1.0 if vu >= 1

gen interact_vu = dummy_vu * vu

* REGRESSIONS 
global WAGE "gw"
global CF1 "cf1"
global CF10 "cf10"
global GCPI "gcpi"

keep period gcpi vu gw magpty grpe grpf cf1 cf10 shortage diffcpicf CPIENGSL CPIUFDSL dummyq2_2020 dummyq3_2020 dummy_vu interact_vu
keep if period>=tq(1989:1) & period<=tq(2023:2)

******* Specification 1 *******
reg gw vu interact_vu dummyq2_2020 dummyq3_2020

******* Specification 2 *******
reg gw vu interact_vu l1.gw dummyq2_2020 dummyq3_2020 

outreg2 using specification_2.doc, replace ctitle(Specification 2) stats(coef se pval)

******* Specification 3 *******
reg gw l1.vu l1.interact_vu l1.gw dummyq2_2020 dummyq3_2020 
