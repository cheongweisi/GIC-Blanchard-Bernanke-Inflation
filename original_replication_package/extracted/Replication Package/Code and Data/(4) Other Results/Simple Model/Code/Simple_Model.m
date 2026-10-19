% This script runs both dynare files and save output in excel format 
% Created by James Lee and Athiana Tettaravou 
clear;

% Change directories as needed

base_dir = pwd();
output_dir = "..\Replication Package\Code and Data\(4) Other Results\Simple Model\Output";
cd(output_dir)

delete("simple_model_irf_results.xls");
excel_file = 'simple_model_irf_results';

period = (1:20)';

%% Run Dynare file for weak response and save results
cd(base_dir)
dynare Simple_Eq_simulations_weak
cd(output_dir)
xlswrite(excel_file,{"period"}, 'Weak_Response', 'A1')
xlswrite(excel_file,period, 'Weak_Response', 'A2');
xlswrite(excel_file,{"p_eta_u"}, 'Weak_Response', 'B1')
xlswrite(excel_file, p_eta_u, 'Weak_Response', 'B2');
xlswrite(excel_file,{"p_eta_zp"}, 'Weak_Response', 'C1')
xlswrite(excel_file, p_eta_zp, 'Weak_Response', 'C2');

%% Run Dynare file for strong response and save results
cd(base_dir)
dynare Simple_Eq_simulations_strong 
cd(output_dir)
xlswrite(excel_file,{"period"}, 'Strong_Response', 'A1')
xlswrite(excel_file,period, 'Strong_Response', 'A2');
xlswrite(excel_file, p_eta_u,'Strong_Response', 'B2');
xlswrite(excel_file,{"p_eta_u"}, 'Strong_Response', 'B1')
xlswrite(excel_file, p_eta_zp, 'Strong_Response', 'C2');
xlswrite(excel_file,{"p_eta_zp"}, 'Strong_Response', 'C1')
