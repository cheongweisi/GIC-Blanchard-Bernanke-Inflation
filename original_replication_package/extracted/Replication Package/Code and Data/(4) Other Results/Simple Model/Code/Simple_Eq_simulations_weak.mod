% This script requires the Dynare package (4.5 or higher) 
% Follow instructions at https://www.dynare.org/download/ to install the Dynare package and specify the appropriate path folder.
% More instructions on the readme file 
 
close all;

% This file gives results for the strong feedback case. 
%----------------------------------------------------------------
%  VARIABLES
%----------------------------------------------------------------
var w pe p pistar u zw zp pip piw; 
varexo eta_zw eta_zp eta_u;

parameters  beta alphaa be gamma rho_zw rho_zp rho_u;

%----------------------------------------------------------------
% CALIBRATION 
%----------------------------------------------------------------
beta    	= 0.9;	
alphaa		= 0.2;			
be   		= 0.2;				
gamma 		= 0.95;		

rho_zw   = 0.00;
rho_zp 	= 0.00;
rho_u = 0.00;

%----------------------------------------------------------------
% MODEL
%----------------------------------------------------------------

model(linear); 
    w = w(-1)+pe-p(-1)+alphaa*(p(-1)-pe(-1))-be*(u-alphaa*u(-1))+zw;
    p = w+zp;
    pe = p(-1)+beta*pistar+(1-beta)*(p(-1)-p(-2));	
    pistar = gamma*pistar(-1)+(1-gamma)*(p(-1)-p(-2));
	zw = rho_zw*zw(-1)+eta_zw;
	zp = rho_zp*zp(-1)+eta_zp;
	u = rho_u*u(-1)-eta_u;
    pip = p-p(-1);
    piw = w-w(-1);
end;

shocks;
var eta_zw;  stderr 1.00;
var eta_zp;  stderr 1.00;
var eta_u;  stderr 1.00;
end;

stoch_simul(order=1,irf=20)w p;

myvar1 = oo_.irfs.p_eta_zp;
myvar2 = oo_.irfs.p_eta_u;
