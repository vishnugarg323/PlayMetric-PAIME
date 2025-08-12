// MUI types fix
import { styled } from '@mui/material/styles';
import MuiGrid from '@mui/material/Grid';

export const StyledGrid = styled(MuiGrid)(({ }) => ({
  // Add any custom styles here
}));

// This is a workaround for the Grid typing issues
export const Grid = StyledGrid as typeof MuiGrid;
