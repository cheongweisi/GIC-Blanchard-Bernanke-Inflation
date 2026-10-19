function [residual, g1, g2] = dynamic_resid_g1_g2(T, y, x, params, steady_state, it_, T_flag)
% function [residual, g1, g2] = dynamic_resid_g1_g2(T, y, x, params, steady_state, it_, T_flag)
%
% Wrapper function automatically created by Dynare
%

    if T_flag
        T = Simple_Eq_simulations_weak.dynamic_g2_tt(T, y, x, params, steady_state, it_);
    end
    [residual, g1] = Simple_Eq_simulations_weak.dynamic_resid_g1(T, y, x, params, steady_state, it_, false);
    g2       = Simple_Eq_simulations_weak.dynamic_g2(T, y, x, params, steady_state, it_, false);

end
