import { useState } from "react";
import {
  Box,
  TextField,
  Button,
  Typography,
  Card,
  CardContent,
  Stack,
  Divider,
} from "@mui/material";
import axios from "axios";

const endpointMapping = {
  Notion: "notion",
  Airtable: "airtable",
  HubSpot: "hubspot",
};

function ItemCard({ item }) {
  return (
    <Card
      variant="outlined"
      sx={{ mb: 2, background: "#fafbfc", borderRadius: 2 }}
    >
      <CardContent>
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          {item.type}
        </Typography>
        <Typography variant="h6" sx={{ mb: 1 }}>
          {item.name || <span style={{ color: "#bbb" }}>[No Name]</span>}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          <b>ID:</b> {item.id}
        </Typography>
        {item.creation_time && (
          <Typography variant="body2" color="text.secondary">
            <b>Created:</b> {item.creation_time}
          </Typography>
        )}
        {item.last_modified_time && (
          <Typography variant="body2" color="text.secondary">
            <b>Last Modified:</b> {item.last_modified_time}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}

export const DataForm = ({ integrationType, credentials }) => {
  const [loadedData, setLoadedData] = useState(null);
  const endpoint = endpointMapping[integrationType];

  const handleLoad = async () => {
    try {
      const formData = new FormData();
      formData.append("credentials", JSON.stringify(credentials));
      const response = await axios.post(
        `http://localhost:8000/integrations/${endpoint}/load`,
        formData
      );
      const data = response.data;
      setLoadedData(data);
    } catch (e) {
      alert(e?.response?.data?.detail);
    }
  };

  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      flexDirection="column"
      width="100%"
    >
      <Box display="flex" flexDirection="column" width="100%">
        <Stack spacing={2} sx={{ width: "100%", mt: 2 }}>
          {Array.isArray(loadedData) && loadedData.length > 0 ? (
            loadedData.map((item, idx) => (
              <ItemCard key={item.id || idx} item={item} />
            ))
          ) : loadedData ? (
            <Typography color="text.secondary" sx={{ mt: 2 }}>
              [No items found]
            </Typography>
          ) : null}
        </Stack>
        <Button onClick={handleLoad} sx={{ mt: 2 }} variant="contained">
          Load Data
        </Button>
        <Button
          onClick={() => setLoadedData(null)}
          sx={{ mt: 1 }}
          variant="contained"
        >
          Clear Data
        </Button>
      </Box>
    </Box>
  );
};
