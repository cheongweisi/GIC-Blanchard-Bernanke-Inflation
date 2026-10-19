# The following file generates plots of predicted versus actual values in the restricted equations. 
# Note that the wage and inflations expectations equations are estimated on the pre-COVID sample and an out of sample
# prediction is performed. For the price equation, because of the shortage variable, we estimate over the entire sample. 

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

setwd("../Replication Package/Code and Data/(2) Regressions/Output Data (Restricted Sample)/")

# Import data
eq_simulations_data <- read_excel("eq_simulations_data_restricted.xls")

# Filter out period. 
eq_simulations_data %<>%
  filter(
    period >= "2019-12-01"
  )

eq_simulations_data$period <- as.yearqtr(eq_simulations_data$period, format = "%Y-%m-%d")

# This recreates the graph from Figure 3. 
plot1 <- ggplot(data = eq_simulations_data) +
  labs(title = "Figure 3. WAGE GROWTH, 2020 Q1 - 2023 Q1.", x = "X-AXIS TITLE", y = "Percent") + 
  geom_line(mapping = aes(x = period, y = gw, color = "Actual"), linewidth = 1.25) +
  geom_line(mapping = aes(x = period, y = gwf1, color = "Predicted"), linewidth = 1.25) +
  scale_colour_manual("", 
                      breaks = c("Actual", "Predicted"),
                      values = c("darkblue", "darkred")) +
  theme_bw() + theme(legend.position = "bottom",
                     # legend.key.size = unit(3, 'cm'), #change legend key size
                     legend.key.height = unit(.5, 'cm'), #change legend key height
                     legend.key.width = unit(2, 'cm'), #change legend key width
                     legend.text = element_text(size=12), # change legend key font size
                     legend.background = element_rect(colour = 'black', fill = 'white', linetype='solid'),
                     legend.title = element_text(angle = 90, hjust = .5, vjust = 0.5),
                     plot.title = element_text(size=17.5),
                     panel.grid.major.x = element_blank(),
                     panel.grid.minor.x = element_blank(),
                     panel.grid.minor.y = element_blank(),
                     axis.line = element_line("black"),
                     axis.title.x = element_blank(),
                     axis.title.y = element_text(size = 16), 
                     axis.text.x = element_text(size=16, color = "black"),
                     axis.text.y = element_text(size=16, color = "black"),
                     panel.border = element_blank(), 
                     plot.caption = element_text(hjust = 0)
  ) + coord_fixed(ratio = 0.15) +
  scale_x_yearqtr(expand = c(.05, .02), breaks = seq(from = min(eq_simulations_data$period), to = max(eq_simulations_data$period), by = .5), format = "%Y Q%q", n = 8)

ggsave(plot1)


# This recreates the graph from Figure 7. 
plot2 <- ggplot(data = eq_simulations_data) +
  labs(title = "Figure 7. INFLATION, 2020 Q1 - 2023 Q1.", x = "X-AXIS TITLE", y = "Percent") + 
  geom_line(mapping = aes(x = period, y = gcpi, color = "Actual"), linewidth = 1.25) +
  geom_line(mapping = aes(x = period, y = gcpif, color = "Predicted"), linewidth = 1.25) +
  scale_colour_manual("", 
                      breaks = c("Actual", "Predicted"),
                      values = c("darkblue", "darkred")) +
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
                     axis.title.x = element_blank(),
                     axis.title.y = element_text(size = 16), 
                     axis.text.x = element_text(size=16, color = "black"),
                     axis.text.y = element_text(size=16, color = "black"),
                     panel.border = element_blank(), 
                     plot.caption = element_text(hjust = 0)
  ) + coord_fixed(ratio = 0.08) +
  scale_x_yearqtr(expand = c(.05, .02), breaks = seq(from = min(eq_simulations_data$period), to = max(eq_simulations_data$period), by = .5), format = "%Y Q%q", n = 8) +
  scale_y_continuous(limits = c(-2, 12), expand = c(.05, .01), breaks = c(-2,0,2,4,6,8,10, 12) )

ggsave(plot2)

# This recreates the graph from Figure 8. 
plot3 <- ggplot(data = eq_simulations_data) +
  labs(title = "Figure 8. SHORT-RUN INFLATION EXPECTATIONS, 2020 Q1 - 2023 Q1.", x = "X-AXIS TITLE", y = "Percent") + 
  geom_line(mapping = aes(x = period, y = cf1, color = "Actual"), linewidth = 1.25) +
  geom_line(mapping = aes(x = period, y = cf1f, color = "Predicted"), linewidth = 1.25) +
  scale_colour_manual("", 
                      breaks = c("Actual", "Predicted"),
                      values = c("darkblue", "darkred")) +
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
                     axis.title.x = element_blank(),
                     axis.title.y = element_text(size = 16), 
                     axis.text.x = element_text(size=16, color = "black"),
                     axis.text.y = element_text(size=16, color = "black"),
                     panel.border = element_blank(), 
                     plot.caption = element_text(hjust = 0)
  ) + coord_fixed(ratio = 0.35) +
  scale_x_yearqtr(expand = c(.05, .02), breaks = seq(from = min(eq_simulations_data$period), to = max(eq_simulations_data$period), by = .5), format = "%Y Q%q", n = 8) 

ggsave(plot3)

# This recreates the graph from Figure 9. 
plot4 <- ggplot(data = eq_simulations_data) +
  labs(title = "Figure 9. LONG-RUN INFLATION EXPECTATIONS, 2020 Q1 - 2023 Q1.", x = "X-AXIS TITLE", y = "Percent") + 
  geom_line(mapping = aes(x = period, y = cf10, color = "Actual"), linewidth = 1.25) +
  geom_line(mapping = aes(x = period, y = cf10f, color = "Predicted"), linewidth = 1.25) +
  scale_colour_manual("", 
                      breaks = c("Actual", "Predicted"),
                      values = c("darkblue", "darkred")) +
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
                     axis.title.x = element_blank(),
                     axis.title.y = element_text(size = 16), 
                     axis.text.x = element_text(size=16, color = "black"),
                     axis.text.y = element_text(size=16, color = "black"),
                     panel.border = element_blank(), 
                     plot.caption = element_text(hjust = 0)
  ) + coord_fixed(ratio = 1) +
  scale_x_yearqtr(expand = c(.05, .02), breaks = seq(from = min(eq_simulations_data$period), to = max(eq_simulations_data$period), by = .5), format = "%Y Q%q", n = 8) +
  scale_y_continuous(limits = c(1, 2.5), expand = c(.05, .01), breaks = c(-1,1.2,1.4,1.6,1.8,2.0, 2.2, 2.4) )

ggsave(plot4)

rm(eq_simulations_data)
