# The following file plots figure 6. 

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
library(ggplot2)
library(ggpubr)


# Change file path (WD)
setwd("../Replication Package/Code and Data/(1) Data/Public Data/")

figure_6 <- read_excel("figure_6_car_data.xlsx")

figure_6$Date <- as.yearqtr(figure_6$Date, format = "%Y-%m-%d")

assemblies <- ggplot(data = figure_6) +
  labs(title = "Motor Vehicle Assemblies", x = "X-AXIS TITLE", y = "Millions of Units") + 
  geom_line(mapping = aes(x = Date, y = MVATOTASSS), color = "darkblue", linewidth = 1.25) +
  theme_bw() + theme(legend.position = "bottom",
                     # legend.key.size = unit(3, 'cm'), #change legend key size
                     legend.key.height = unit(.5, 'cm'), #change legend key height
                     legend.key.width = unit(2, 'cm'), #change legend key width
                     legend.text = element_text(size=12), # change legend key font size
                     legend.background = element_rect(colour = 'black', fill = 'white', linetype='solid'),
                     legend.title = element_text(angle = 90, hjust = .5, vjust = 0.5),
                     plot.title = element_text(size=17.5),
                     # panel.grid.major.x = element_blank(),
                     panel.grid.minor.x = element_blank(),
                     panel.grid.minor.y = element_blank(),
                     axis.line = element_line("black"),
                     axis.title.x = element_blank(),
                     axis.title.y = element_text(size = 14), 
                     axis.text.x = element_text(size=14, color = "black"),
                     axis.text.y = element_text(size=14, color = "black"),
                     panel.border = element_blank(), 
                     axis.ticks.length = unit(.2, "cm")
  ) + # coord_fixed(ratio = .2) + 
  scale_y_continuous(breaks = c(3,6,9,12), limits = c(3,12)) + 
  scale_x_yearqtr(breaks = seq(from = min(figure_6$Date), to = max(figure_6$Date), by = .25), format = "%Y", 
                  labels = c("2018", "", "", "", "2019", "","","","2020", "", "", "", "2021", "", "", "", "2022", "", "", "", "2023"))

AUINSA <- ggplot(data = figure_6) +
  labs(title = "Auto Inventories", x = "X-AXIS TITLE", y = "Thousands of Units") + 
  geom_line(mapping = aes(x = Date, y = AUINSA), color = "darkblue", linewidth = 1.25) +
  theme_bw() + theme(legend.position = "bottom",
                     # legend.key.size = unit(3, 'cm'), #change legend key size
                     legend.key.height = unit(.5, 'cm'), #change legend key height
                     legend.key.width = unit(2, 'cm'), #change legend key width
                     legend.text = element_text(size=12), # change legend key font size
                     legend.background = element_rect(colour = 'black', fill = 'white', linetype='solid'),
                     legend.title = element_text(angle = 90, hjust = .5, vjust = 0.5),
                     plot.title = element_text(size=17.5),
                     # panel.grid.major.x = element_blank(),
                     panel.grid.minor.x = element_blank(),
                     panel.grid.minor.y = element_blank(),
                     axis.line = element_line("black"),
                     axis.title.x = element_blank(),
                     axis.title.y = element_text(size = 14), 
                     axis.text.x = element_text(size=14, color = "black"),
                     axis.text.y = element_text(size=14, color = "black"),
                     panel.border = element_blank(), 
                     axis.ticks.length = unit(.2, "cm")
  ) + # coord_fixed(ratio = .0015) + 
  scale_y_continuous(breaks = c(0,250,500,750,1000), limits = c(0,1000)) + 
  scale_x_yearqtr(breaks = seq(from = min(figure_6$Date), to = max(figure_6$Date), by = .25), format = "%Y", 
                  labels = c("2018", "", "", "", "2019", "","","","2020", "", "", "", "2021", "", "", "", "2022", "", "", "", "2023"))

inflation <- ggplot(data = figure_6) +
  labs(title = "Inflation in New Vehicle Prices (PCE)", x = "X-AXIS TITLE", y = "Percent (Annualized)") + 
  geom_line(mapping = aes(x = Date, y = NV_Change_Annualized), color = "darkblue", linewidth = 1.25) +
  theme_bw() + theme(legend.position = "bottom",
                     # legend.key.size = unit(3, 'cm'), #change legend key size
                     legend.key.height = unit(.5, 'cm'), #change legend key height
                     legend.key.width = unit(2, 'cm'), #change legend key width
                     legend.text = element_text(size=12), # change legend key font size
                     legend.background = element_rect(colour = 'black', fill = 'white', linetype='solid'),
                     legend.title = element_text(angle = 90, hjust = .5, vjust = 0.5),
                     plot.title = element_text(size=17.5),
                     # panel.grid.major.x = element_blank(),
                     panel.grid.minor.x = element_blank(),
                     panel.grid.minor.y = element_blank(),
                     axis.line = element_line("black"),
                     axis.title.x = element_blank(),
                     axis.title.y = element_text(size = 14), 
                     axis.text.x = element_text(size=14, color = "black"),
                     axis.text.y = element_text(size=14, color = "black"),
                     panel.border = element_blank(), 
                     axis.ticks.length = unit(.2, "cm")
  ) + # coord_fixed(ratio = .1) + 
  scale_y_continuous(breaks = c(0,5,10,15,20), limits = c(-2,20)) + 
  scale_x_yearqtr(breaks = seq(from = min(figure_6$Date), to = max(figure_6$Date), by = .25), format = "%Y", 
                  labels = c("2018", "", "", "", "2019", "","","","2020", "", "", "", "2021", "", "", "", "2022", "", "", "", "2023"))

google <- ggplot(data = figure_6) +
  labs(title = "Google Searches", x = "X-AXIS TITLE", y = "Index (2021 Q3 = 100)") + 
  geom_line(mapping = aes(x = Date, y = chipshortage, color = "Chip Shortage"), linewidth = 1.25) +
  geom_line(mapping = aes(x = Date, y = carshortage, color = "Car Shortage"), linewidth = 1.25) +
  scale_colour_manual("", 
                      breaks = c("Chip Shortage", "Car Shortage"),
                      values = c("darkblue", "darkred")) +
  theme_bw() + theme(legend.position = c(.1825, .775),
                     legend.margin = margin(0, 5, 5, 5),
                     # legend.key.size = unit(3, 'cm'), #change legend key size
                     legend.key.height = unit(.5, 'cm'), #change legend key height
                     legend.key.width = unit(2, 'cm'), #change legend key width
                     legend.text = element_text(size=12), # change legend key font size
                     legend.text.align = 0, 
                     legend.background = element_rect(colour = 'black', fill = 'white', linetype='solid'),
                     legend.title = element_text(angle = 90, hjust = .5, vjust = 0.5),
                     plot.title = element_text(size=17.5),
                     # panel.grid.major.x = element_blank(),
                     panel.grid.minor.x = element_blank(),
                     panel.grid.minor.y = element_blank(),
                     axis.line = element_line("black"),
                     axis.title.x = element_blank(),
                     axis.title.y = element_text(size = 14), 
                     axis.text.x = element_text(size=14, color = "black"),
                     axis.text.y = element_text(size=14, color = "black"),
                     panel.border = element_blank(), 
                     axis.ticks.length = unit(.2, "cm")
  ) + # coord_fixed(ratio = .01) + 
  scale_y_continuous(breaks = c(0,25,50,75,100,125), limits = c(0,125)) + 
  scale_x_yearqtr(breaks = seq(from = min(figure_6$Date), to = max(figure_6$Date), by = .25), format = "%Y", 
                  labels = c("2018", "", "", "", "2019", "","","","2020", "", "", "", "2021", "", "", "", "2022", "", "", "", "2023"))

google

g1 <- ggplotGrob(assemblies)
g2 <- ggplotGrob(AUINSA)
g3 <- ggplotGrob(inflation)
g4 <- ggplotGrob(google)

g <- rbind(g1, g2, g3, g4, size = "first")

g$widths <- unit.pmax(g1$widths, g2$widths, g3$widths, g4$widths)

grid.newpage()
grid.draw(g)

ggsave(g)

