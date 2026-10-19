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
library(xlsx)

gscpi <- read_excel("Dropbox/Bernanke_Blanchard/AEJ Macro/Replication Package/Code and Data/(5) Appendix/Shortage Alternatives/gscpi_data.xls", 
                    sheet = "GSCPI Monthly Data")

gscpi %>%
  select(
    Date, GSCPI
  ) %>% filter(
    !row_number() %in% c(1, 2, 3, 4)
  ) -> gscpi

gscpi$Date = as_date(gscpi$Date, format = "%d-%b-%Y")

gscpi %>%
  group_by(Date = paste(lubridate::year(Date), quarters(Date))) %>%
  summarise(gscpi = mean(GSCPI)) -> gscpi

gscpi %>%
  filter(
    Date == "2019 Q1" | Date == "2019 Q2"| Date == "2019 Q3"| Date == "2019 Q4"
  ) %>% summarise(
    mean = mean(gscpi)
  )

# write.xlsx(gscpi, file = "Dropbox/Bernanke_Blanchard/AEJ Macro/Replication Package/Code and Data/(5) Appendix/Shortage Alternatives/shortage_cleaned.xlsx")


### ISM
ism <- read_excel("ism.xlsx")

ism %>% na.omit() %>%
  filter(
    !row_number() %in% c(1:252)
  ) -> ism

ism$Date <- parse_date_time(ism$Date, "%b %y")

ism %>%
  group_by(Date = paste(lubridate::year(Date), quarters(Date))) %>%
  summarise(ISM = mean(ISM)) -> ism

write.xlsx(ism, file = "ism_cleaned.xlsx")

