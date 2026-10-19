# The following file generates plots for the decompositions in Bernanke Blanchard. 

# Import packages
library(tidyverse)
library(magrittr)
library(ggplot2)
library(zoo)
library(tseries)
library(readxl)
library(grid)
library(lubridate)
library(reshape2)

# Change this
setwd("../Replication Package/Code and Data/(3) Core Results/Decompositions/Output Data/")

# Decomposition of Prices
remove_all <- read_excel("remove_all.xls")
remove_grpe <- read_excel("remove_grpe.xls")
remove_grpf <- read_excel("remove_grpf.xls")
remove_vu <- read_excel("remove_vu.xls")
remove_short <- read_excel("remove_shortage.xls")
remove_magpty <- read_excel("remove_magpty.xls")
remove_q2 <- read_excel("remove_2020q2.xls")
remove_q3 <- read_excel("remove_2020q3.xls")


decomp_data <- bind_cols(remove_all$period, remove_all$gcpi_simul,
                         remove_grpe$grpe_contr_gcpi,
                         remove_grpf$grpf_contr_gcpi,
                         remove_short$shortage_contr_gcpi, 
                         remove_vu$vu_contr_gcpi, 
                         remove_magpty$magpty_contr_gcpi,
                         remove_q2$dummy2020_q2_contr_gcpi, 
                         remove_q3$dummy2020_q3_contr_gcpi)

actual_cpi <- bind_cols(remove_all$period, remove_all$gcpi)

decomp_data %<>%
  rename(
    period = "...1",
    `Initial Conditions` = "...2",
    `Energy Prices` = "...3", 
    `Food Prices` = "...4", 
    `Shortages` = "...5", 
    `V/U` = "...6", 
    `Productivity` = "...7",
    `Q2 Dummy` = "...8",
    `Q3 Dummy` = "...9"
  ) %<>% filter(
    period >= "2019-07-01"
  )

actual_cpi %<>%
  rename(
    period = "...1",
    actual = "...2"
  ) %<>% filter(
    period >= "2019-07-01"
  )

decomp_data$period <- as.yearqtr(decomp_data$period, format = "%Y-%m-%d")
actual_cpi$period <- as.yearqtr(actual_cpi$period, format = "%Y-%m-%d")

decomp_data %<>% melt(id = "period")
decomp_data$variable <- factor(decomp_data$variable, levels = c("Shortages",
                                                                "Energy Prices",
                                                                "Food Prices",
                                                                "V/U",
                                                                "Productivity",
                                                                "Q2 Dummy", 
                                                                "Q3 Dummy",
                                                                "Initial Conditions"))

plot1 <- ggplot() +
  geom_bar(data = decomp_data, mapping = aes(x = period, y = value, fill = variable), stat = "identity", width = .1) + 
  geom_line(data = actual_cpi, mapping = aes(x = as.numeric(period), y = actual, color = "Actual Inflation"), linewidth = 1.25) + 
  scale_colour_manual(NULL, values=c(`Actual Inflation` = "black", `Predicted Inflation` = "black")) +
  labs(title = "Figure 12. THE SOURCES OF PRICE INFLATION, 2020 Q1 to 2023 Q1", x = "Quarter", y = "Percent") + 
  scale_fill_manual(name = NULL, 
                    values = c(`Initial Conditions` = "grey",
                               `V/U` = "red",
                               `Energy Prices` = "blue",
                               `Food Prices` = "skyblue",
                               `Shortages` = "gold",
                               `Productivity` = "orange", 
                               `Q2 Dummy` = "darkgreen",
                               `Q3 Dummy` = "lightgreen")) + 
  theme_bw() + theme(legend.position = "bottom",
                     # legend.key.size = unit(3, 'cm'), #change legend key size
                     legend.key.height = unit(.47, 'cm'), #change legend key height
                     legend.key.width = unit(2, 'cm'), #change legend key width
                     legend.text = element_text(size=12), # change legend key font size
                     legend.background = element_rect(colour = 'black', fill = 'white', linetype='solid'),
                     legend.title = element_text(angle = 90, hjust = .5, vjust = 0.5),
                     plot.title = element_text(size=17.5),
                     panel.grid.major.x = element_blank(),
                     panel.grid.minor.x = element_blank(),
                     panel.grid.minor.y = element_blank(),
                     axis.line = element_line("black"),
                     axis.title.x = element_text(size = 16),
                     axis.title.y = element_text(size = 16),
                     axis.text.x = element_text(size=16, color = "black"),
                     axis.text.y = element_text(size=16, color = "black"),
                     panel.border = element_blank(), 
                     plot.caption = element_text(hjust = 0),
  ) + coord_fixed(ratio = .1) +
  scale_x_yearqtr(expand = c(.05, .02), breaks = seq(from = min(decomp_data$period), to = max(decomp_data$period), by = .5), format = "%Y Q%q") +
  scale_y_continuous(expand = c(.05, .02), breaks = seq(from = -4, to = 11, by = 2))

ggsave(plot1)

# Decomposition of Wages

decomp_data <- bind_cols(remove_all$period, remove_all$gw_simul,
                         remove_grpe$grpe_contr_gw,
                         remove_grpf$grpf_contr_gw,
                         remove_short$shortage_contr_gw, 
                         remove_vu$vu_contr_gw, 
                         remove_magpty$magpty_contr_gw,
                         remove_q2$dummy2020_q2_contr_gw, 
                         remove_q3$dummy2020_q3_contr_gw)

actual_gw <- bind_cols(remove_all$period, remove_all$gw)

decomp_data %<>%
  rename(
    period = "...1",
    `Initial Conditions` = "...2",
    `Energy Prices` = "...3", 
    `Food Prices` = "...4", 
    `Shortages` = "...5", 
    `V/U` = "...6", 
    `Productivity` = "...7",
    `Q2 Dummy` = "...8",
    `Q3 Dummy` = "...9"
  ) %<>% filter(
    period >= "2019-07-01"
  )

actual_gw %<>%
  rename(
    period = "...1",
    actual = "...2"
  ) %<>% filter(
    period >= "2019-07-01"
  )

decomp_data$period <- as.yearqtr(decomp_data$period, format = "%Y-%m-%d")
actual_gw$period <- as.yearqtr(actual_gw$period, format = "%Y-%m-%d")

decomp_data %<>% melt(id = "period")
decomp_data$variable <- factor(decomp_data$variable, levels = c("Shortages",
                                                                "Energy Prices",
                                                                "Food Prices",
                                                                "V/U",
                                                                "Productivity",
                                                                "Q2 Dummy", 
                                                                "Q3 Dummy",
                                                                "Initial Conditions"))

plot2 <- ggplot() +
  geom_bar(data = decomp_data, mapping = aes(x = period, y = value, fill = variable), stat = "identity", width = .1) + 
  geom_line(data = actual_gw, mapping = aes(x = as.numeric(period), y = actual, color = "Actual Inflation"), linewidth = 1.25) + 
  labs(title = "Figure 13. THE SOURCES OF WAGE INFLATION, 2020 Q1 to 2023 Q1", x = "Quarter", y = "Percent") + 
  scale_colour_manual(NULL, values=c(`Actual Inflation` = "black")) +
  scale_fill_manual(name = NULL, 
                    values = c(`Initial Conditions` = "grey",
                               `V/U` = "red",
                               `Energy Prices` = "blue",
                               `Food Prices` = "skyblue",
                               `Shortages` = "gold",
                               `Productivity` = "orange",
                               `Q2 Dummy` = "darkgreen",
                               `Q3 Dummy` = "lightgreen")) + 
  theme_bw() + theme(legend.position = "bottom",
                     # legend.key.size = unit(3, 'cm'), #change legend key size
                     legend.key.height = unit(.47, 'cm'), #change legend key height
                     legend.key.width = unit(2, 'cm'), #change legend key width
                     legend.text = element_text(size=12), # change legend key font size
                     legend.background = element_rect(colour = 'black', fill = 'white', linetype='solid'),
                     legend.title = element_text(angle = 90, hjust = .5, vjust = 0.5),
                     plot.title = element_text(size=17.5),
                     panel.grid.major.x = element_blank(),
                     panel.grid.minor.x = element_blank(),
                     panel.grid.minor.y = element_blank(),
                     axis.line = element_line("black"),
                     axis.title.x = element_text(size = 16),
                     axis.title.y = element_text(size = 16),
                     axis.text.x = element_text(size=16, color = "black"),
                     axis.text.y = element_text(size=16, color = "black"),
                     panel.border = element_blank(), 
                     plot.caption = element_text(hjust = 0),
  ) + coord_fixed(ratio = .15) +
  scale_x_yearqtr(expand = c(.05, .02), breaks = seq(from = min(decomp_data$period), to = max(decomp_data$period), by = .5), format = "%Y Q%q") +
  scale_y_continuous(expand = c(.05, .02), breaks = seq(from = -4, to = 10, by = 2))

ggsave(plot2)