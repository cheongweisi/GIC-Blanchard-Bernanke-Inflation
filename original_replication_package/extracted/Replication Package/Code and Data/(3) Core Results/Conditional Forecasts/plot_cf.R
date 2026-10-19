# The following file generates plots of the extension in which we begin the estimation in which we add
# nominal gdp to the price equation. 

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

# Change working directory.
setwd("../Replication Package/Code and Data/(3) Core Results/Conditional Forecasts/Output Data/")

# Conditional forecast
terminal_high <- read_excel("terminal_high.xlsx")
terminal_mid <- read_excel("terminal_mid.xlsx")
terminal_low <- read_excel("terminal_low.xlsx")

cf_data <- bind_cols(terminal_low$period, terminal_low$gcpi_simul, terminal_mid$gcpi_simul, terminal_high$gcpi_simul)

cf_data %<>% 
  rename(
    period = "...1",
    low = "...2",
    mid = "...3", 
    high = "...4"
  ) %<>% filter(
    period >= "2022-12-01" & period <= "2027-01-01"
  )

cf_data$period <- as.yearqtr(cf_data$period, format = "%Y-%m-%d")

# Plot Figure 14
plot1 <- ggplot(data = cf_data) +
  labs(title = "Figure 14. Inflation projections for alternative paths of v/u.", x = "Quarter", y = "Percent") + 
  geom_line(mapping = aes(x = period, y = low, color = "v/u = 0.8"), linewidth = 1.25) +
  geom_line(mapping = aes(x = period, y = mid, color = "v/u = 1.2 = (v/u)*"), linewidth = 1.25) +
  geom_line(mapping = aes(x = period, y = high, color = "v/u = 1.8"), linewidth = 1.25) +
  scale_colour_manual("", 
                      breaks = c("v/u = 0.8", "v/u = 1.2 = (v/u)*", "v/u = 1.8"),
                      values = c("darkblue", "darkred", "orange")) +
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
  ) + coord_fixed(ratio = .6) +
  scale_x_yearqtr(expand = c(.05, .02), breaks = seq(from = min(cf_data$period), to = max(cf_data$period), by = .5), format = "%Y Q%q") +
  scale_y_continuous(expand = c(.05, .02), breaks = seq(from = 2.0, to = 5.0, by = .5))

rm(terminal_high, terminal_low, terminal_mid, cf_data)

ggsave(plot1)
