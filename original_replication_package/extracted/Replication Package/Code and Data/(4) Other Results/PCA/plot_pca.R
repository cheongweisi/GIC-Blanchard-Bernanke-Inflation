# The following file plots figures 4 and 5. 

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
library(haven)

# Change WD
setwd("../Replication Package/")

pca <- read_excel("Code and Data/(4) Other Results/PCA/Bloomberg_Commodity_Data_Cleaned_Quarterly.xlsx")

pca %>%
  filter(Date >= "2019-12-31") %>%
  mutate(
    Date = as.yearqtr(Date, format = "%Y-%m-%d")
  ) -> pca

Regression_Data <- read_excel("Code and Data/(1) Data/Public Data/Regression_Data.xlsx")

Regression_Data %>%
  select(Date, CPIUFDSL, CPIENGSL) %>%
  filter(Date >= "2020 Q1") %>%
  mutate(
    Date = as.yearqtr(Date)
  ) -> Regression_Data

data <- left_join(Regression_Data, pca, by = "Date")


###################
# Plot Energy PCA #
###################

max_first  <- max(pca$CRB_PC)   # Specify max of first y axis
max_second <- max(Regression_Data$CPIENGSL) # Specify max of second y axis
min_first  <- min(pca$CRB_PC)   # Specify min of first y axis
min_second <- min(Regression_Data$CPIENGSL) # Specify min of second y axis

# scale and shift variables calculated based on desired mins and maxes
scale = (max_second - min_second)/(max_first - min_first)
shift = min_first - min_second

# Function to scale secondary axis
scale_function <- function(x, scale, shift){
  return ((x)*scale - shift)
}

# Function to scale secondary variable values
inv_scale_function <- function(x, scale, shift){
  return ((x + shift)/scale)
}

plot1 <- ggplot(data = data) +
  labs(title = "Energy PCA Graph", x = "X-AXIS TITLE", y = "Percent") + 
  geom_line(mapping = aes(x = Date, y = CRB_PC, color = "1st Principal Component"), linewidth = 1.25) +
  geom_line(mapping = aes(x = Date, y = inv_scale_function(CPIENGSL, scale, shift), color = "CPI Energy Index"), linewidth = 1.25) +
  scale_colour_manual("", 
                      breaks = c("1st Principal Component", "CPI Energy Index"),
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
  ) + coord_fixed(ratio = .1) + 
  scale_x_yearqtr(expand = c(.05, .02), format = "%Y Q%q") + 
  scale_y_continuous(breaks = seq(from = 0, to = 8, by = 2),
    
    # Features of the first axis
    name = "1st Principal Component",
    
    # Add a second axis and specify its features
    sec.axis = sec_axis(trans=~scale_function(., scale, shift), name="CPI Energy Index", breaks = seq(from = 180, to = 320, by = 20))
  )

ggsave(plot1)
#################
# Plot Food PCA #
#################

max_first  <- max(pca$CRB_PC)   # Specify max of first y axis
max_second <- max(Regression_Data$CPIUFDSL) # Specify max of second y axis
min_first  <- min(pca$CRB_PC)   # Specify min of first y axis
min_second <- min(Regression_Data$CPIUFDSL) # Specify min of second y axis

# scale and shift variables calculated based on desired mins and maxes
scale = (max_second - min_second)/(max_first - min_first)
shift = min_first - min_second

# Function to scale secondary axis
scale_function <- function(x, scale, shift){
  return ((x)*scale - shift)
}

# Function to scale secondary variable values
inv_scale_function <- function(x, scale, shift){
  return ((x + shift)/scale)
}

plot2 <- ggplot(data = data) +
  labs(title = "Food PCA Graph", x = "X-AXIS TITLE", y = "Percent") + 
  geom_line(mapping = aes(x = Date, y = CRB_PC, color = "1st Principal Component"), linewidth = 1.25) +
  geom_line(mapping = aes(x = Date, y = inv_scale_function(CPIUFDSL, scale, shift), color = "CPI Food Index"), linewidth = 1.25) +
  scale_colour_manual("", 
                      breaks = c("1st Principal Component", "CPI Food Index"),
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
  ) + coord_fixed(ratio = .1) + 
  scale_x_yearqtr(expand = c(.05, .02), format = "%Y Q%q") + 
  scale_y_continuous(breaks = seq(from = 0, to = 8, by = 2),
                     
                     # Features of the first axis
                     name = "1st Principal Component",
                     
                     # Add a second axis and specify its features
                     sec.axis = sec_axis(trans=~scale_function(., scale, shift), name="CPI Food Index", breaks = seq(from = 260, to = 320, by = 20))
  )

ggsave(plot2)



  

