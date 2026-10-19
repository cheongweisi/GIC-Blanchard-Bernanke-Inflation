clear all
close all
clc

%% Current analysis: standard specification.
% Need to change:
% 1) the cd() file path,
% 2) the data names for the data and coefficients
% 3) the export data file names.

%% README
% This file generates figures 10 and 11 from Bernanke and Blanchard (2023).

%% Set CD
cd("..\Replication Package\Code and Data\(2) Regressions\Output Data (Full Sample)")

output_dir = "..\Replication Package\Code and Data\(3) Core Results\IRFs\Output Data";

%% Import and format data
% All data is initialized to zero to reflect that they are in steady state
format long

data = readtable("eq_simulations_data.xls", VariableNamingRule="preserve");
table_q4_data = data(data.period >= datetime(2020,01,1), :);
data = data(data.period >= datetime(2018,10,1), :);

%% Specify combinations shocks that we are interested in. 

% Specification for Figure 10 (energy prices). Copy this function and edit
% to write your own specifications. Paste below. 
results_energy = irfs(data, table_q4_data, ...
    [true, ... % Shock to energy prices (grpe).
     false, ... % Shock to food prices (grpf).
     false, ... % Shock to v/u. 
     false, ... % Shock to shortages. 
     false, ... % Shock to wages (gw). 
     false, ... % Shock to prices (gcpi). 
     false, ... % Shock to short run expections (cf1).
     false], ... % Shock to long run expectations (cf10).
    [0.0, ... % Persistence parameter for grpe. 
     0.0, ... % Persistence parameter for grpf. 
     1.0, ... % Persistence parameter for v/u.
     0.0, ... % Persistence parameter for shortages.
     0.0, ... % Persistence parameter for wages (gw).
     0.0, ... % Persistence parameter for prices (gcpi).
     0.0, ... % Persistence parameter for short run expectations (cf1).
     0.0]);   % Persistence parameter for long run expectations (cf10).

% Specification for Figure 10 (food prices). 
results_food = irfs(data, table_q4_data, ...
    [false, true, false, false, false, false, false, false], ... 
    [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]);

% Specification for Figure 11 (v/u). 
results_vu = irfs(data, table_q4_data, ...
    [false, false, true, false, false, false, false, false], ...
    [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]);

% Specification for Figure 10 (shortages).
results_shortage = irfs(data, table_q4_data, ...
    [false, false, false, true, false, false, false, false], ...
    [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]);

%% Export Data (Change directory using cd() or ignore).
cd(output_dir)

writetable(results_energy, "results_energy.xls")
writetable(results_food, "results_food.xls")
writetable(results_vu, "results_vu.xls")
writetable(results_shortage, "results_shortage.xls")

%% Function to run impulse response functions with specified shocks.

function results = irfs(data, table_q4_data, shocks, rho)

    % Input estimated coefficients. (This can be modified to include
    % different coefficient estimates.)
    gw_beta = readtable("eq_coefficients.xlsx", 'Sheet', "gw");
    gcpi_beta = readtable("eq_coefficients.xlsx", 'Sheet', "gcpi");
    cf1_beta = readtable("eq_coefficients.xlsx", 'Sheet', "cf1");
    cf10_beta = readtable("eq_coefficients.xlsx", 'Sheet', "cf10");
    
    % Initialize rho.
    rho_grpe = rho(1);
    rho_grpf = rho(2);
    rho_vu = rho(3);
    rho_shortage = rho(4);
    rho_gw = rho(5);
    rho_gcpi = rho(6);
    rho_cf1 = rho(7);
    rho_cf10 = rho(8);

    % Initialize shocks.
    add_grpe_shock = shocks(1);
    add_grpf_shock = shocks(2);
    add_vu_shock = shocks(3);
    add_shortage_shock = shocks(4);
    add_gw_shock = shocks(5);
    add_gcpi_shock = shocks(6);
    add_cf1_shock = shocks(7);
    add_cf10_shock = shocks(8);

    % Capture shocks added.
    shocks_added = {};
    step = 1;

    if add_grpe_shock
        shocks_added{step} = "grpe";
        step = step + 1;
    end
    
    if add_grpf_shock
        shocks_added{step} = "grpf";
        step = step + 1;
    end
    
    if add_vu_shock
        shocks_added{step} = "vu";
        step = step + 1;
    end
    
    if add_shortage_shock
        shocks_added{step} = "shortage";
        step = step + 1;
    end
    
    if add_gw_shock
        shocks_added{step} = "gw";
        step = step + 1;
    end
    
    if add_gcpi_shock
        shocks_added{step} = "gcpi";
        step = step + 1;
    end
    
    if add_cf1_shock
        shocks_added{step} = "cf1";
        step = step + 1;
    end
    
    if add_cf10_shock
        shocks_added{step} = "cf10";
        step = step + 1;
    end
    
    % Initialize shocks.
    shock_grpe = zeros(1,4);
    shock_grpf = zeros(1,4);
    shock_vu = zeros(1,4);
    shock_shortage = zeros(1,4);
    shock_gw = zeros(1,4);
    shock_gcpi = zeros(1,4);
    shock_cf1 = zeros(1,4);
    shock_cf10 = zeros(1,4);

    % Define time horizon
    timesteps = 32;
    period = data.period.';

    % Initialize empty vectors to contain results.
    gw = zeros(1,timesteps);
    cf1 = zeros(1,timesteps);
    magpty = zeros(1,timesteps);
    diffcpicf = zeros(1,timesteps);
    vu = zeros(1,timesteps);
    gcpi = zeros(1,timesteps);
    grpe = zeros(1,timesteps);
    grpf = zeros(1,timesteps);
    shortage = zeros(1,timesteps);
    cf10 = zeros(1,timesteps);

    % Since we need 4 values before we can run the simulation (because we have
    % 4 lags), we need to initialize the first 4 values of cf1_simul to the
    % actual data
    gw_simul = gw(1:4);
    gcpi_simul = gcpi(1:4);
    cf1_simul = cf1(1:4);
    cf10_simul = cf10(1:4);
    diffcpicf_simul = diffcpicf(1:4);

    % We also define four values for the exogenous variablers.
    grpe_shock_series = grpe(1:4);
    grpf_shock_series = grpf(1:4);
    vu_shock_series = vu(1:4);
    shortage_shock_series = shortage(1:4);

    % Calcuate shock values based on data. We conduct a 1 standard
    % deviation shock in all cases.
    shock_val_grpe = 1*std(table_q4_data.grpe, "omitnan");
    shock_val_grpf = 1*std(table_q4_data.grpf, "omitnan");
    shock_val_vu = 1*std(table_q4_data.vu, "omitnan");
    shock_val_shortage = 1*std(table_q4_data.shortage, "omitnan");
    shock_val_gw_residual = 1*std(table_q4_data.gw_residuals, "omitnan");
    shock_val_gcpi_residual = 1*std(table_q4_data.gcpi_residuals, "omitnan");
    shock_val_cf1_residual = 1*std(table_q4_data.cf1_residuals, "omitnan");
    shock_val_cf10_residual = 1*std(table_q4_data.cf10_residuals, "omitnan");


    % Run and calculate impulse response functions. 
    for t = 5:timesteps

    % Equation adding shocks. It equals zero unless the specified
    % conditions are met.
        shock_grpe(t) = 0;
        shock_grpf(t) = 0;
        shock_vu(t) = 0;
        shock_shortage(t) = 0;
        shock_gw(t) = 0;
        shock_gcpi(t) = 0;
        shock_cf1(t) = 0;
        shock_cf10(t) = 0;

        if add_grpe_shock && t == 5 % one time increase to rate, i.e. permanent increase in level
            shock_grpe(t) = shock_val_grpe;
        end
    
        if add_grpf_shock && t == 5 % one time increase to rate, i.e. permanent increase in level
            shock_grpf(t) = shock_val_grpf;
        end
    
        if add_vu_shock && t == 5 % permanent increase in level (due to rho)
            shock_vu(t) = shock_val_vu;
        end
    
        if add_shortage_shock && t == 5 % one time increase
            shock_shortage(t) = shock_val_shortage;
        end
    
        if add_gw_shock && t == 5 % one time increase
            shock_gw(t) = shock_val_gw_residual;
        end
    
        if add_gcpi_shock && t == 5 % one time increase
            shock_gcpi(t) = shock_val_gcpi_residual;
        end
    
        if add_cf1_shock && t == 5 % one time increase
            shock_cf1(t) = shock_val_cf1_residual;
        end
    
        if add_cf10_shock && t == 5 % one time increase
            shock_cf10(t) = shock_val_cf10_residual;
        end

        grpe_shock_series(t) = rho_grpe*grpe_shock_series(t-1) + shock_grpe(t);
        grpf_shock_series(t) = rho_grpf*grpf_shock_series(t-1) + shock_grpf(t);
        vu_shock_series(t) = rho_vu*vu_shock_series(t-1) + shock_vu(t);
        shortage_shock_series(t) = rho_shortage*shortage_shock_series(t-1) + shock_shortage(t);

        % We now run the formal simulation. 
        % Wage equation
        if add_gw_shock && t == 5
            gw_simul(t) = rho_gw * gw_simul(t-1) + shock_gw(t);
        else
            gw_simul(t) = gw_beta.beta(1) * gw_simul(t-1) + ...
            gw_beta.beta(2) * gw_simul(t-2) + ...
            gw_beta.beta(3) * gw_simul(t-3) + ...
            gw_beta.beta(4) * gw_simul(t-4) + ...
            gw_beta.beta(5) * cf1_simul(t-1) + ...
            gw_beta.beta(6) * cf1_simul(t-2) + ...
            gw_beta.beta(7) * cf1_simul(t-3) + ...
            gw_beta.beta(8) * cf1_simul(t-4) + ...
            gw_beta.beta(9) * magpty(t-1) + ...
            gw_beta.beta(10) * vu_shock_series(t-1) + ...
            gw_beta.beta(11) * vu_shock_series(t-2) + ...
            gw_beta.beta(12) * vu_shock_series(t-3) + ...
            gw_beta.beta(13) * vu_shock_series(t-4) + ...
            gw_beta.beta(14) * diffcpicf_simul(t-1) + ...
            gw_beta.beta(15) * diffcpicf_simul(t-2) + ...
            gw_beta.beta(16) * diffcpicf_simul(t-3) + ...
            gw_beta.beta(17) * diffcpicf_simul(t-4);
        end

        % Price equation
        if add_gcpi_shock && t == 5
            gcpi_simul(t) = rho_gcpi * gcpi_simul(t-1) + shock_gcpi(t);
        else
            gcpi_simul(t) =  gcpi_beta.beta(1) * magpty(t) + ...
            gcpi_beta.beta(2) * gcpi_simul(t-1) + ...
            gcpi_beta.beta(3) * gcpi_simul(t-2) + ...
            gcpi_beta.beta(4) * gcpi_simul(t-3) + ...
            gcpi_beta.beta(5) * gcpi_simul(t-4) + ...
            gcpi_beta.beta(6) * gw_simul(t) + ...
            gcpi_beta.beta(7) * gw_simul(t-1) + ...
            gcpi_beta.beta(8) * gw_simul(t-2) + ...
            gcpi_beta.beta(9) * gw_simul(t-3) + ...
            gcpi_beta.beta(10) * gw_simul(t-4) + ...
            gcpi_beta.beta(11) * grpe_shock_series(t) + ...
            gcpi_beta.beta(12) * grpe_shock_series(t-1) + ...
            gcpi_beta.beta(13) * grpe_shock_series(t-2) + ...
            gcpi_beta.beta(14) * grpe_shock_series(t-3) + ...
            gcpi_beta.beta(15) * grpe_shock_series(t-4) + ...
            gcpi_beta.beta(16) * grpf_shock_series(t) + ...
            gcpi_beta.beta(17) * grpf_shock_series(t-1) + ...
            gcpi_beta.beta(18) * grpf_shock_series(t-2) + ...
            gcpi_beta.beta(19) * grpf_shock_series(t-3) + ...
            gcpi_beta.beta(20) * grpf_shock_series(t-4) + ...
            gcpi_beta.beta(21) * shortage_shock_series(t) + ...
            gcpi_beta.beta(22) * shortage_shock_series(t-1) + ...
            gcpi_beta.beta(23) * shortage_shock_series(t-2) + ...
            gcpi_beta.beta(24) * shortage_shock_series(t-3) + ...
            gcpi_beta.beta(25) * shortage_shock_series(t-4);
        end

        % Catch up equation
        diffcpicf_simul(t) = 0.25*(gcpi_simul(t) + gcpi_simul(t-1) + ...
            gcpi_simul(t-2) + gcpi_simul(t-3)) - cf1_simul(t-4);

        % Long run expectations
        if add_cf10_shock && t == 5
            cf10_simul(t) = rho_cf10 * cf10_simul(t-1) + shock_cf10(t);
        else
            cf10_simul(t) = cf10_beta.beta(1) * cf10_simul(t-1) + ...
            cf10_beta.beta(2) * cf10_simul(t-2) + ...
            cf10_beta.beta(3) * cf10_simul(t-3) + ...
            cf10_beta.beta(4) * cf10_simul(t-4) + ...
            cf10_beta.beta(5) * gcpi_simul(t) + ...
            cf10_beta.beta(6) * gcpi_simul(t-1) + ...
            cf10_beta.beta(7) * gcpi_simul(t-2) + ...
            cf10_beta.beta(8) * gcpi_simul(t-3) + ...
            cf10_beta.beta(9) * gcpi_simul(t-4);
        end
        
        % Short run expectations
        if add_cf1_shock && t == 5
            cf1_simul(t) = rho_cf1 * cf1_simul(t-1) + shock_cf1(t);
        else
            cf1_simul(t) = cf1_beta.beta(1) * cf1_simul(t-1) + ...
            cf1_beta.beta(2) * cf1_simul(t-2) + ...
            cf1_beta.beta(3) * cf1_simul(t-3) + ...
            cf1_beta.beta(4) * cf1_simul(t-4) + ...
            cf1_beta.beta(5) * cf10_simul(t) + ...
            cf1_beta.beta(6) * cf10_simul(t-1) + ...
            cf1_beta.beta(7) * cf10_simul(t-2) + ...
            cf1_beta.beta(8) * cf10_simul(t-3) + ...
            cf1_beta.beta(9) * cf10_simul(t-4) + ...
            cf1_beta.beta(10) * gcpi_simul(t) + ...
            cf1_beta.beta(11) * gcpi_simul(t-1) + ...
            cf1_beta.beta(12) * gcpi_simul(t-2) + ...
            cf1_beta.beta(13) * gcpi_simul(t-3) + ...
            cf1_beta.beta(14) * gcpi_simul(t-4);
        end

    end

    results = table((1:timesteps).', gw_simul.', gcpi_simul.', ...
    cf1_simul.', cf10_simul.', diffcpicf_simul.', grpe_shock_series.', ...
    grpf_shock_series.', vu_shock_series.', shortage_shock_series.', ...
    'VariableNames',["period", "gw_simul", "gcpi_simul", "cf1_simul", ...
    "cf10_simul", "diffcpicf_simul", "grpe_shock_series", ...
    "grpf_shock_series", "vu_shock_series", "shortage_shock_series"]);

end



